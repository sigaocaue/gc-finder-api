"""Router de líderes — listagem pública e CRUD autenticado."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.leader import LeaderCreate, LeaderResponse, LeaderUpdate
from app.services.leader_service import LeaderService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/leaders", tags=["líderes"])


# --- Rotas públicas ---


@router.get("/", response_model=ApiResponse[list[LeaderResponse]])
async def list_leaders(db: DbSession):
    """Lista todos os líderes ativos (rota pública)."""
    service = LeaderService(db)
    leaders = await service.list_all()
    return ApiResponse(
        data=[LeaderResponse.model_validate(l) for l in leaders],
        message="Lista de líderes",
    )


@router.get("/{leader_id}", response_model=ApiResponse[LeaderResponse])
async def get_leader(leader_id: UUID, db: DbSession):
    """Busca um líder pelo ID (rota pública)."""
    service = LeaderService(db)
    leader = await service.get_by_id(leader_id)
    if leader is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Líder não encontrado",
        )
    return ApiResponse(
        data=LeaderResponse.model_validate(leader),
        message="Líder encontrado",
    )


# --- Rotas autenticadas ---


@router.post("/", response_model=ApiResponse[LeaderResponse], status_code=status.HTTP_201_CREATED)
async def create_leader(body: LeaderCreate, current_user: CurrentUser, db: DbSession):
    """Cria um novo líder (requer autenticação)."""
    service = LeaderService(db)
    leader = await service.create(body)
    return ApiResponse(
        data=LeaderResponse.model_validate(leader),
        message="Líder criado com sucesso",
    )


@router.put("/{leader_id}", response_model=ApiResponse[LeaderResponse])
async def update_leader(
    leader_id: UUID,
    body: LeaderUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Atualiza os dados de um líder (requer autenticação)."""
    service = LeaderService(db)
    leader = await service.update(leader_id, body)
    if leader is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Líder não encontrado",
        )
    return ApiResponse(
        data=LeaderResponse.model_validate(leader),
        message="Líder atualizado com sucesso",
    )


@router.delete("/{leader_id}", response_model=ApiResponse[LeaderResponse])
async def deactivate_leader(leader_id: UUID, current_user: CurrentUser, db: DbSession):
    """Desativa um líder (requer autenticação)."""
    service = LeaderService(db)
    leader = await service.deactivate(leader_id)
    if leader is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Líder não encontrado",
        )
    return ApiResponse(
        data=LeaderResponse.model_validate(leader),
        message="Líder desativado com sucesso",
    )
