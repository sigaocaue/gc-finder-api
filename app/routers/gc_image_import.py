"""Rotas de importação de GC por imagem (extração OCR + salvamento)."""

import asyncio
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.gc import GcResponse
from app.schemas.gc_image_import import (
    GcHeartbeatEvent,
    GcImportSaveRequest,
    GcImportStartResponse,
    GcJobStatusEvent,
    ImageImportForm,
)
from app.services.gc_image_import_service import (
    ALLOWED_EXTENSIONS,
    MAX_IMAGE_SIZE,
    get_job_state,
    process_image_job,
    start_job,
)
from app.services.gc_image_save_service import GcImageSaveService
from app.services.ocr.factory import validate_ocr_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/gcs/import",
    tags=["GC Import"],
)


@router.post(
    "/image",
    response_model=ApiResponse[GcImportStartResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Iniciar extração de GC por imagem",
    description="Envia imagem(ns) via upload ou URL para extração de dados via OCR.",
)
async def start_image_import(
    current_user: CurrentUser,
    form: ImageImportForm = Depends(),
) -> ApiResponse[GcImportStartResponse]:
    """Inicia a extração assíncrona de dados de GC a partir de imagens."""
    # Valida o serviço OCR escolhido (o enum garante valores válidos,
    # mas ainda precisamos checar disponibilidade no ambiente)
    try:
        validated_ocr = validate_ocr_service(form.ocr_service.value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    images = form.images
    provided_image_names = [
        upload.filename
        for upload in (images or [])
        if upload and upload.filename
    ]
    # Normaliza URLs: o frontend pode enviar como itens separados ou como
    # uma única string JSON/separada por vírgula dentro de um único campo
    raw_urls = _normalize_url_list(form.images_urls or [])
    provided_image_urls = [
        url.strip()
        for url in raw_urls
        if url and url.strip()
    ]
    logger.info(
        "[gc_image_import] User %s (%s) requested image import "
        "(files=%s, urls=%s, ocr=%s)",
        current_user.id,
        current_user.email,
        provided_image_names,
        provided_image_urls,
        form.ocr_service.value,
    )
    has_files = images and any(f.filename for f in images)
    has_urls = bool(raw_urls)

    if not has_files and not has_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie pelo menos uma imagem (arquivo ou URL).",
        )

    errors: list[str] = []
    saved_paths: list[Path] = []
    url_list: list[str] = []

    # Validação de arquivos enviados
    if has_files:
        for idx, upload in enumerate(images):
            if not upload.filename:
                continue

            ext = Path(upload.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                errors.append(
                    f"Extensão '{ext}' não permitida para '{upload.filename}'. "
                    f"Extensões aceitas: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                )
                continue

            content = await upload.read()
            if len(content) > MAX_IMAGE_SIZE:
                errors.append(
                    f"Imagem '{upload.filename}' excede o tamanho máximo de 5MB."
                )
                continue

            tmp_path = Path(tempfile.gettempdir()) / f"gc_import_{idx}_{upload.filename}"
            tmp_path.write_bytes(content)
            saved_paths.append(tmp_path)

    # Validação de URLs
    if has_urls:
        for idx, raw_url in enumerate(raw_urls):
            stripped = raw_url.strip()
            if not stripped:
                errors.append(f"images_urls[{idx}]: URL vazia não é permitida.")
                continue

            parsed = urlparse(stripped)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                errors.append(
                    f"images_urls[{idx}]: '{stripped}' não é uma URL válida."
                )
                continue

            url_list.append(stripped)

    # Retorna todos os erros acumulados de uma vez
    if errors:
        # Limpa arquivos temporários salvos antes do erro
        for path in saved_paths:
            path.unlink(missing_ok=True)

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=errors,
        )

    # Cria o job
    job_id = await start_job(saved_paths, url_list)

    # Renomeia arquivos temporários com o job_id
    renamed_paths: list[Path] = []
    for idx, path in enumerate(saved_paths):
        new_path = Path(tempfile.gettempdir()) / f"{job_id}_{idx}{path.suffix}"
        path.rename(new_path)
        renamed_paths.append(new_path)

    # Dispara processamento em background
    asyncio.create_task(
        process_image_job(job_id, renamed_paths, url_list, validated_ocr)
    )
    logger.info("[gc_image_import] Job %s iniciado em background", job_id)

    stream_url = f"/api/v1/gcs/import/jobs/{job_id}/stream"

    return ApiResponse(
        data=GcImportStartResponse(
            job_id=job_id,
            status="pending",
            stream_url=stream_url,
        ),
        message="Extração iniciada. Acompanhe o progresso pelo stream_url.",
    )


@router.get(
    "/jobs/{job_id}/stream",
    summary="Acompanhar progresso da extração via SSE",
    description="Retorna Server-Sent Events com o progresso da extração de imagem.",
)
async def stream_job_status(
    job_id: str,
    current_user: CurrentUser,
) -> StreamingResponse:
    """Stream SSE com atualizações de status do job de extração."""
    logger.info(
        "[gc_image_import] User %s (%s) requested job stream %s",
        current_user.id,
        current_user.email,
        job_id,
    )

    # Verifica se o job existe
    initial_state = await get_job_state(job_id)
    if initial_state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado.",
        )

    async def event_generator():
        last_status = None
        last_progress = None
        heartbeat_counter = 0

        while True:
            state = await get_job_state(job_id)

            if state is None:
                event = GcJobStatusEvent(
                    status="failed",
                    error="Job não encontrado ou expirado.",
                )
                yield event.to_sse()
                break

            current_status = state.get("status")
            current_progress = state.get("progress")

            # Emite evento se houve mudança de estado
            if current_status != last_status or current_progress != last_progress:
                heartbeat_counter = 0

                if current_status == "done":
                    event = GcJobStatusEvent(
                        status="done",
                        result=state.get("result"),
                    )
                    yield event.to_sse()
                    break
                elif current_status == "failed":
                    event = GcJobStatusEvent(
                        status="failed",
                        error=state.get("error"),
                    )
                    yield event.to_sse()
                    break
                else:
                    event = GcJobStatusEvent(
                        status=current_status,
                        progress=current_progress,
                    )
                    yield event.to_sse()

                last_status = current_status
                last_progress = current_progress
            else:
                heartbeat_counter += 1

            # Heartbeat a cada 15 segundos (15 iterações de 1s)
            if heartbeat_counter >= 15:
                heartbeat_counter = 0
                heartbeat = GcHeartbeatEvent(
                    ts=datetime.now(timezone.utc).isoformat(),
                )
                yield heartbeat.to_sse()

            await asyncio.sleep(1)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/save",
    response_model=ApiResponse[GcResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Salvar GC importado no banco de dados",
    description="Recebe os dados extraídos (revisados ou não) e cadastra o GC completo.",
)
async def save_imported_gc(
    body: GcImportSaveRequest,
    current_user: CurrentUser,
    db: DbSession,
):
    """Cadastra GC, líderes, contatos e encontros no banco de dados."""
    logger.info(
        "[gc_image_import] User %s (%s) saving imported GC "
        "name=%s street=%s city=%s state=%s leaders=%s meetings=%s",
        current_user.id,
        current_user.email,
        body.name,
        body.street,
        body.city,
        body.state,
        len(body.leaders),
        len(body.meetings),
    )
    # Validação de campos obrigatórios
    if not body.name or not body.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O campo 'name' é obrigatório.",
        )
    if not body.street or not body.street.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O campo 'street' é obrigatório.",
        )

    service = GcImageSaveService(db)
    gc = await service.save(body)

    return ApiResponse(
        data=GcResponse.model_validate(gc),
        message="GC cadastrado com sucesso.",
    )


def _normalize_url_list(raw_items: list[str]) -> list[str]:
    """Normaliza a lista de URLs recebida via Form multipart.

    O frontend pode enviar as URLs de diferentes formas:
    - Campos separados (cada URL é um item na lista) → já está correto
    - Um único campo com JSON array: '["url1","url2"]' → precisa fazer parse
    - Um único campo separado por vírgula: 'url1,url2' → precisa fazer split
    """
    if not raw_items:
        return []

    result: list[str] = []
    for item in raw_items:
        stripped = item.strip()
        if not stripped:
            result.append(item)
            continue

        # Tenta parse como JSON array
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    result.extend(str(v) for v in parsed)
                    continue
            except (json.JSONDecodeError, ValueError):
                pass

        # Tenta split por vírgula (somente se contiver vírgula e não parecer URL única)
        if "," in stripped and "://" in stripped:
            parts = [p.strip() for p in stripped.split(",")]
            if all("://" in p for p in parts if p):
                result.extend(parts)
                continue

        result.append(item)

    return result
