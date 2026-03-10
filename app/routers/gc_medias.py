"""Router de mídias do GC — imagens, vídeos e posts do Instagram vinculados a um GC."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.gc_media import GcMediaCreate, GcMediaResponse, GcMediaUpdate
from app.services.gc_service import GcService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gcs/{gc_id}/medias", tags=["mídias"])


# --- Rota pública ---


@router.get("/", response_model=ApiResponse[list[GcMediaResponse]])
async def list_medias(gc_id: UUID, db: DbSession):
    """Lista todas as mídias de um GC (rota pública)."""
    service = GcService(db)
    medias = await service.list_medias(gc_id)
    return ApiResponse(
        data=[GcMediaResponse.model_validate(m) for m in medias],
        message="Lista de mídias",
    )


# --- Rotas autenticadas ---


@router.post("/", response_model=ApiResponse[GcMediaResponse], status_code=status.HTTP_201_CREATED)
async def create_media(gc_id: UUID, body: GcMediaCreate, current_user: CurrentUser, db: DbSession):
    """Cria uma nova mídia para o GC (requer autenticação)."""
    service = GcService(db)
    media = await service.create_media(gc_id, body)
    return ApiResponse(
        data=GcMediaResponse.model_validate(media),
        message="Mídia criada com sucesso",
    )


@router.put("/{media_id}", response_model=ApiResponse[GcMediaResponse])
async def update_media(
    gc_id: UUID,
    media_id: UUID,
    body: GcMediaUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Atualiza uma mídia do GC (requer autenticação)."""
    service = GcService(db)
    media = await service.update_media(gc_id, media_id, body)
    return ApiResponse(
        data=GcMediaResponse.model_validate(media),
        message="Mídia atualizada com sucesso",
    )


@router.delete("/{media_id}", response_model=ApiResponse)
async def delete_media(gc_id: UUID, media_id: UUID, current_user: CurrentUser, db: DbSession):
    """Remove uma mídia do GC (requer autenticação)."""
    service = GcService(db)
    await service.delete_media(gc_id, media_id)
    return ApiResponse(message="Mídia removida com sucesso")
