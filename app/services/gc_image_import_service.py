"""Serviço de importação de GC por imagem — orquestra OCR, parsing, geocoding e Redis."""

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import redis.asyncio as aioredis

from app.config import settings
from app.services.geocoding_service import fetch_coordinates
from app.services.image_parser_service import parse_ocr_text
from app.services.ocr_service import extract_text

logger = logging.getLogger(__name__)

JOB_TTL_SECONDS = 3600
JOB_KEY_PREFIX = "gc_import_job"

# Extensões de imagem permitidas
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB


def _normalize_text_field(value: str | None) -> str:
    """Garante que apenas strings limpas sejam consideradas válidas para validações."""
    if isinstance(value, str):
        return value.strip()
    return ""


def _get_redis() -> aioredis.Redis:
    """Cria um cliente Redis a partir da URL de configuração."""
    return aioredis.from_url(settings.redis_url, decode_responses=True)


def _job_key(job_id: str) -> str:
    return f"{JOB_KEY_PREFIX}:{job_id}"


async def _set_job_state(
    redis_client: aioredis.Redis,
    job_id: str,
    *,
    status: str,
    progress: str | None = None,
    result: dict | None = None,
    error: str | None = None,
    created_at: str | None = None,
) -> None:
    """Persiste o estado do job no Redis."""
    key = _job_key(job_id)

    # Busca estado atual para preservar created_at
    if created_at is None:
        current = await redis_client.get(key)
        if current:
            created_at = json.loads(current).get("created_at")

    state = {
        "job_id": job_id,
        "status": status,
        "progress": progress,
        "result": result,
        "error": error,
        "created_at": created_at or datetime.now(timezone.utc).isoformat(),
    }
    await redis_client.set(key, json.dumps(state, ensure_ascii=False), ex=JOB_TTL_SECONDS)


async def get_job_state(job_id: str) -> dict | None:
    """Busca o estado de um job no Redis."""
    redis_client = _get_redis()
    try:
        raw = await redis_client.get(_job_key(job_id))
        if raw is None:
            return None
        return json.loads(raw)
    finally:
        await redis_client.aclose()


async def start_job(
    image_paths: list[Path],
    image_urls: list[str],
) -> str:
    """Cria um job de extração e retorna o job_id."""
    job_id = str(uuid.uuid4())
    sources_desc = []
    if image_paths:
        sources_desc.append(f"{len(image_paths)} arquivo(s)")
    if image_urls:
        sources_desc.append(f"{len(image_urls)} URL(s)")

    logger.info(
        "[gc_image_import] Job %s criado — source=%s",
        job_id,
        ", ".join(sources_desc),
    )

    redis_client = _get_redis()
    try:
        await _set_job_state(
            redis_client,
            job_id,
            status="pending",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    finally:
        await redis_client.aclose()

    return job_id


async def process_image_job(
    job_id: str,
    image_paths: list[Path],
    image_urls: list[str],
) -> None:
    """Processa o job de extração em background."""
    redis_client = _get_redis()
    temp_files: list[Path] = []

    try:
        logger.info("[gc_image_import] Job %s iniciado em background", job_id)

        # --- Etapa 1: Download de URLs para arquivos temporários ---
        all_image_paths = list(image_paths)

        if image_urls:
            await _set_job_state(
                redis_client,
                job_id,
                status="processing",
                progress="Baixando imagens das URLs...",
            )
            for idx, url in enumerate(image_urls):
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.get(url)
                        response.raise_for_status()

                    # Determina extensão a partir da URL ou content-type
                    ext = ".jpg"
                    for allowed_ext in ALLOWED_EXTENSIONS:
                        if url.lower().endswith(allowed_ext):
                            ext = allowed_ext
                            break

                    tmp_path = Path(tempfile.gettempdir()) / f"{job_id}_url_{idx}{ext}"
                    tmp_path.write_bytes(response.content)
                    temp_files.append(tmp_path)
                    all_image_paths.append(tmp_path)
                except Exception as exc:
                    logger.error(
                        "[gc_image_import] Falha ao baixar URL %s: %s", url, exc
                    )
                    await _set_job_state(
                        redis_client,
                        job_id,
                        status="failed",
                        error=f"Falha ao baixar imagem da URL: {url}",
                    )
                    return

        if not all_image_paths:
            await _set_job_state(
                redis_client,
                job_id,
                status="failed",
                error="Nenhuma imagem disponível para processamento.",
            )
            return

        # --- Etapa 2: OCR em todas as imagens ---
        await _set_job_state(
            redis_client,
            job_id,
            status="processing",
            progress="Executando OCR na imagem...",
        )

        all_texts: list[str] = []
        for img_path in all_image_paths:
            texts = await extract_text(str(img_path))
            all_texts.extend(texts)

        if not all_texts:
            await _set_job_state(
                redis_client,
                job_id,
                status="failed",
                error="Nenhum texto foi detectado na imagem.",
            )
            return

        # --- Etapa 3: Parsing com regex ---
        await _set_job_state(
            redis_client,
            job_id,
            status="processing",
            progress="Estruturando dados extraídos...",
        )

        extracted = parse_ocr_text(all_texts)
        name = _normalize_text_field(extracted.name)
        street = _normalize_text_field(extracted.street)

        # Valida campos mínimos (nome + logradouro)
        if not name or not street:
            await _set_job_state(
                redis_client,
                job_id,
                status="failed",
                error="Não foi possível extrair nome e endereço da imagem.",
            )
            return

        # --- Etapa 4: Geocoding ---
        await _set_job_state(
            redis_client,
            job_id,
            status="processing",
            progress="Buscando coordenadas no Google Maps...",
        )

        full_address = (
            f"{extracted.street}, {extracted.number or 's/n'}, "
            f"{extracted.neighborhood or ''}, {extracted.city} - "
            f"{extracted.state}, Brasil"
        )
        logger.info("[geocoding] Query: \"%s\"", full_address)

        coords = await fetch_coordinates(full_address)
        if coords:
            extracted.latitude = coords[0]
            extracted.longitude = coords[1]
            logger.info(
                "[geocoding] Resultado: lat=%s, lng=%s",
                coords[0],
                coords[1],
            )

            # Tenta obter CEP via geocoding reverso
            try:
                from app.services.geocoding_service import fetch_address_from_cep
                # CEP será preenchido pelo frontend ou na rota de save
            except Exception:
                pass
        else:
            logger.warning("[geocoding] Falha no geocoding — salvando sem coordenadas")

        # --- Etapa 5: Concluído ---
        await _set_job_state(
            redis_client,
            job_id,
            status="done",
            result=extracted.model_dump(mode="json"),
        )
        logger.info("[gc_image_import] Job %s concluído: status=done", job_id)

    except Exception as exc:
        logger.error("[gc_image_import] Job %s falhou: %s", job_id, exc)
        await _set_job_state(
            redis_client,
            job_id,
            status="failed",
            error=str(exc),
        )
    finally:
        # Limpa arquivos temporários (uploads e downloads de URL)
        for path in image_paths:
            try:
                if path.exists():
                    os.unlink(path)
            except OSError:
                pass
        for path in temp_files:
            try:
                if path.exists():
                    os.unlink(path)
            except OSError:
                pass

        await redis_client.aclose()
