"""Serviço de autenticação: login, refresh de tokens e logout."""

import logging
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.utils.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_token,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthService:
    """Serviço responsável pelas operações de autenticação."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    async def login(self, email: str, password: str) -> dict:
        """Valida credenciais e gera par de tokens (access + refresh).

        Armazena o hash do refresh token no banco de dados.
        Retorna dicionário com access_token, refresh_token, token_type e expires_in.
        """
        # Busca o usuário pelo e-mail
        user = await self.user_repo.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="E-mail ou senha inválidos",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário inativo",
            )

        # Cria os tokens
        token_data = {"sub": str(user.id)}
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        # Armazena o hash do refresh token no banco
        refresh_record = RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_expire_days),
        )
        self.db.add(refresh_record)
        await self.db.commit()

        logger.info("Login bem-sucedido para o usuário %s", user.email)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_expire_minutes * 60,
        }

    async def refresh(self, refresh_token_str: str) -> dict:
        """Realiza a rotação de tokens (token rotation).

        Decodifica o refresh token, valida no banco, revoga o antigo e gera um novo par.
        """
        # Decodifica o token
        payload = decode_refresh_token(refresh_token_str)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido ou expirado",
            )

        # Busca o token pelo hash no banco
        token_hash = hash_token(refresh_token_str)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalars().first()

        if stored_token is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token não encontrado",
            )

        # Verifica se já foi revogado
        if stored_token.revoked_at is not None:
            logger.warning(
                "Tentativa de uso de refresh token já revogado (user_id=%s)",
                stored_token.user_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token já foi revogado",
            )

        # Verifica expiração
        if stored_token.expires_at < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expirado",
            )

        # Revoga o token antigo
        stored_token.revoked_at = datetime.now(timezone.utc)

        # Gera novo par de tokens
        token_data = {"sub": str(stored_token.user_id)}
        new_access_token = create_access_token(token_data)
        new_refresh_token = create_refresh_token(token_data)

        # Armazena o novo refresh token
        new_refresh_record = RefreshToken(
            user_id=stored_token.user_id,
            token_hash=hash_token(new_refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.jwt_refresh_expire_days),
        )
        self.db.add(new_refresh_record)
        await self.db.commit()

        logger.info("Refresh de token realizado para user_id=%s", stored_token.user_id)

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_expire_minutes * 60,
        }

    async def logout(self, refresh_token_str: str) -> None:
        """Revoga o refresh token informado."""
        token_hash = hash_token(refresh_token_str)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_token = result.scalars().first()

        if stored_token is not None and stored_token.revoked_at is None:
            stored_token.revoked_at = datetime.now(timezone.utc)
            await self.db.commit()
            logger.info("Logout realizado para user_id=%s", stored_token.user_id)

    async def get_me(self, user: User) -> User:
        """Retorna os dados do usuário autenticado."""
        return user
