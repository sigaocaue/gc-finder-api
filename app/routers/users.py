"""Router de usuários — CRUD completo, restrito a administradores."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import AdminUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/users", tags=["usuários"])


@router.get("/", response_model=ApiResponse[list[UserResponse]])
async def list_users(admin: AdminUser, db: DbSession):
    """Lista todos os usuários cadastrados."""
    service = UserService(db)
    users = await service.list_all()
    return ApiResponse(
        data=[UserResponse.model_validate(u) for u in users],
        message="Lista de usuários",
    )


@router.get("/{user_id}", response_model=ApiResponse[UserResponse])
async def get_user(user_id: UUID, admin: AdminUser, db: DbSession):
    """Busca um usuário pelo ID."""
    service = UserService(db)
    user = await service.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    return ApiResponse(
        data=UserResponse.model_validate(user),
        message="Usuário encontrado",
    )


@router.post("/", response_model=ApiResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(body: UserCreate, admin: AdminUser, db: DbSession):
    """Cria um novo usuário."""
    service = UserService(db)
    user = await service.create(body)
    return ApiResponse(
        data=UserResponse.model_validate(user),
        message="Usuário criado com sucesso",
    )


@router.put("/{user_id}", response_model=ApiResponse[UserResponse])
async def update_user(user_id: UUID, body: UserUpdate, admin: AdminUser, db: DbSession):
    """Atualiza os dados de um usuário existente."""
    service = UserService(db)
    user = await service.update(user_id, body)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    return ApiResponse(
        data=UserResponse.model_validate(user),
        message="Usuário atualizado com sucesso",
    )


@router.delete("/{user_id}", response_model=ApiResponse[UserResponse])
async def deactivate_user(user_id: UUID, admin: AdminUser, db: DbSession):
    """Desativa um usuário (soft delete)."""
    service = UserService(db)
    user = await service.deactivate(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado",
        )
    return ApiResponse(
        data=UserResponse.model_validate(user),
        message="Usuário desativado com sucesso",
    )
