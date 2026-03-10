"""Router de autenticação — login, refresh de token, logout e dados do usuário."""

import logging

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.schemas.common import ApiResponse
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["autenticação"])


@router.post("/login", response_model=ApiResponse[TokenResponse])
async def login(body: LoginRequest, db: DbSession):
    """Autentica o usuário e retorna tokens de acesso e refresh."""
    service = AuthService(db)
    tokens = await service.login(body.email, body.password)
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas",
        )
    return ApiResponse(data=tokens, message="Login realizado com sucesso")


@router.post("/refresh", response_model=ApiResponse[TokenResponse])
async def refresh_token(body: RefreshRequest, db: DbSession):
    """Renova o token de acesso a partir de um refresh token válido."""
    service = AuthService(db)
    tokens = await service.refresh(body.refresh_token)
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido ou expirado",
        )
    return ApiResponse(data=tokens, message="Token renovado com sucesso")


@router.post("/logout", response_model=ApiResponse)
async def logout(body: LogoutRequest, current_user: CurrentUser, db: DbSession):
    """Revoga o refresh token do usuário autenticado."""
    service = AuthService(db)
    await service.logout(body.refresh_token)
    return ApiResponse(message="Logout realizado com sucesso")


@router.get("/me", response_model=ApiResponse[UserResponse])
async def me(current_user: CurrentUser):
    """Retorna os dados do usuário autenticado."""
    return ApiResponse(
        data=UserResponse.model_validate(current_user),
        message="Dados do usuário",
    )
