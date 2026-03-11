"""Router de GCs (Grupos de Convivência) — listagem pública, CRUD autenticado e vínculo de líderes."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.gc import GcCreate, GcDetailResponse, GcLeaderLink, GcResponse, GcUpdate
from app.services.gc_service import GcService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gcs", tags=["GCs"])


# --- Rotas públicas ---


@router.get("/", response_model=ApiResponse[list[GcResponse]])
async def list_gcs(
    db: DbSession,
    skip: int = Query(0, ge=0, description="Registros a pular"),
    limit: int = Query(20, ge=1, le=100, description="Quantidade máxima de registros"),
):
    """Lista todos os GCs ativos com paginação (rota pública)."""
    service = GcService(db)
    gcs = await service.list_all(skip=skip, limit=limit)
    return ApiResponse(
        data=[GcResponse.model_validate(gc) for gc in gcs],
        message="Lista de GCs",
    )


@router.get("/{gc_id}", response_model=ApiResponse[GcDetailResponse])
async def get_gc(gc_id: UUID, db: DbSession):
    """Busca um GC pelo ID com líderes, reuniões e mídias (rota pública)."""
    service = GcService(db)
    gc = await service.get_by_id(gc_id)
    return ApiResponse(data=gc, message="GC encontrado")


# --- Rotas autenticadas ---


@router.post("/", response_model=ApiResponse[GcDetailResponse], status_code=status.HTTP_201_CREATED)
async def create_gc(body: GcCreate, current_user: CurrentUser, db: DbSession) -> ApiResponse[GcDetailResponse]:
    """Cria um novo GC com geocodificação automática do endereço (requer autenticação)."""
    service = GcService(db)
    gc = await service.create(body)
    return ApiResponse(
        data=GcDetailResponse.model_validate(gc),
        message="GC criado com sucesso",
    )


@router.put("/{gc_id}", response_model=ApiResponse[GcDetailResponse])
async def update_gc(gc_id: UUID, body: GcUpdate, current_user: CurrentUser, db: DbSession) -> ApiResponse[GcDetailResponse]:
    """Atualiza os dados de um GC (requer autenticação)."""
    service = GcService(db)
    gc = await service.update(gc_id, body)
    if gc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GC não encontrado",
        )
    return ApiResponse(
        data=GcDetailResponse.model_validate(gc),
        message="GC atualizado com sucesso",
    )


@router.delete("/{gc_id}", response_model=ApiResponse[GcResponse])
async def deactivate_gc(gc_id: UUID, current_user: CurrentUser, db: DbSession):
    """Desativa um GC (requer autenticação)."""
    service = GcService(db)
    gc = await service.deactivate(gc_id)
    if gc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GC não encontrado",
        )
    return ApiResponse(
        data=GcResponse.model_validate(gc),
        message="GC desativado com sucesso",
    )


# --- Vínculo de líderes ---


@router.post("/{gc_id}/leaders", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def link_leader(gc_id: UUID, body: GcLeaderLink, current_user: CurrentUser, db: DbSession):
    """Vincula um líder a um GC (requer autenticação)."""
    service = GcService(db)
    await service.link_leader(gc_id, body.leader_id, body.is_primary)
    return ApiResponse(message="Líder vinculado ao GC com sucesso")


@router.delete("/{gc_id}/leaders/{leader_id}", response_model=ApiResponse)
async def unlink_leader(gc_id: UUID, leader_id: UUID, current_user: CurrentUser, db: DbSession):
    """Remove o vínculo de um líder com um GC (requer autenticação)."""
    service = GcService(db)
    await service.unlink_leader(gc_id, leader_id)
    return ApiResponse(message="Líder desvinculado do GC com sucesso")
