"""Rotas de importação de GC por imagem (extração OCR + salvamento)."""

import asyncio
import json
import logging
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse

from app.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.gc import GcResponse
from app.schemas.gc_image_import import (
    GcExtractedData,
    GcImportSaveRequest,
    GcImportStartResponse,
)
from app.services.gc_image_import_service import (
    ALLOWED_EXTENSIONS,
    MAX_IMAGE_SIZE,
    get_job_state,
    process_image_job,
    start_job,
)
from app.services.gc_image_save_service import GcImageSaveService

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
    image: list[UploadFile] | None = File(None),
    images_urls: list[str] | None = Form(None),
):
    """Inicia a extração assíncrona de dados de GC a partir de imagens."""
    has_files = image and any(f.filename for f in image)
    has_urls = images_urls and any(u.strip() for u in images_urls)

    if not has_files and not has_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Envie pelo menos uma imagem (arquivo ou URL).",
        )

    saved_paths: list[Path] = []
    url_list: list[str] = []

    # Validação e salvamento de arquivos enviados
    if has_files:
        for idx, upload in enumerate(image):
            if not upload.filename:
                continue

            # Valida extensão
            ext = Path(upload.filename).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Extensão '{ext}' não permitida para '{upload.filename}'. "
                        f"Extensões aceitas: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                    ),
                )

            # Valida tamanho (lê o conteúdo)
            content = await upload.read()
            if len(content) > MAX_IMAGE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Imagem '{upload.filename}' excede o tamanho máximo de 5MB."
                    ),
                )

            # Salva em arquivo temporário (gera job_id depois, usa índice no nome)
            tmp_path = Path(tempfile.gettempdir()) / f"gc_import_{idx}_{upload.filename}"
            tmp_path.write_bytes(content)
            saved_paths.append(tmp_path)

    # Valida URLs
    if has_urls:
        url_list = [u.strip() for u in images_urls if u.strip()]

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
        process_image_job(job_id, renamed_paths, url_list)
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
):
    """Stream SSE com atualizações de status do job de extração."""

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
                # Job expirou ou foi removido
                yield _format_sse(
                    "status",
                    {"status": "failed", "error": "Job não encontrado ou expirado."},
                )
                break

            current_status = state.get("status")
            current_progress = state.get("progress")

            # Emite evento se houve mudança de estado
            if current_status != last_status or current_progress != last_progress:
                heartbeat_counter = 0

                if current_status == "done":
                    yield _format_sse(
                        "status",
                        {"status": "done", "result": state.get("result")},
                    )
                    break
                elif current_status == "failed":
                    yield _format_sse(
                        "status",
                        {"status": "failed", "error": state.get("error")},
                    )
                    break
                else:
                    yield _format_sse(
                        "status",
                        {"status": current_status, "progress": current_progress},
                    )

                last_status = current_status
                last_progress = current_progress
            else:
                heartbeat_counter += 1

            # Heartbeat a cada 15 segundos (15 iterações de 1s)
            if heartbeat_counter >= 15:
                heartbeat_counter = 0
                yield _format_sse(
                    "heartbeat",
                    {"ts": datetime.now(timezone.utc).isoformat()},
                )

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


def _format_sse(event: str, data: dict) -> str:
    """Formata um evento SSE."""
    json_data = json.dumps(data, ensure_ascii=False)
    return f"event: {event}\ndata: {json_data}\n\n"
