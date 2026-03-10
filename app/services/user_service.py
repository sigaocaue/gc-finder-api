"""Serviço de gerenciamento de usuários."""

import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate
from app.utils.security import hash_password

logger = logging.getLogger(__name__)


class UserService:
    """Serviço responsável pelas operações de negócio de usuários."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)

    async def list_all(self) -> list[User]:
        """Retorna todos os usuários cadastrados."""
        return await self.repo.get_all()

    async def get_by_id(self, user_id) -> User:
        """Busca um usuário pelo ID. Levanta 404 se não encontrado."""
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        return user

    async def create(self, data: UserCreate) -> User:
        """Cria um novo usuário. Verifica unicidade do e-mail e faz hash da senha."""
        # Verifica se já existe um usuário com este e-mail
        existing = await self.repo.get_by_email(data.email)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Já existe um usuário com este e-mail",
            )

        user = User(
            name=data.name,
            email=data.email,
            password_hash=hash_password(data.password),
            role=data.role,
        )
        user = await self.repo.create(user)
        logger.info("Usuário criado: %s (id=%s)", user.email, user.id)
        return user

    async def update(self, user_id, data: UserUpdate) -> User:
        """Atualiza os dados de um usuário existente."""
        user = await self.get_by_id(user_id)

        update_data = data.model_dump(exclude_unset=True)

        # Se a senha foi informada, faz o hash antes de atualizar
        if "password" in update_data:
            update_data["password_hash"] = hash_password(update_data.pop("password"))

        # Verifica unicidade do e-mail se estiver sendo alterado
        if "email" in update_data and update_data["email"] != user.email:
            existing = await self.repo.get_by_email(update_data["email"])
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Já existe um usuário com este e-mail",
                )

        for field, value in update_data.items():
            setattr(user, field, value)

        user = await self.repo.update(user)
        logger.info("Usuário atualizado: id=%s", user.id)
        return user

    async def deactivate(self, user_id) -> User:
        """Desativa um usuário (soft delete)."""
        user = await self.get_by_id(user_id)
        user = await self.repo.deactivate(user)
        logger.info("Usuário desativado: id=%s", user.id)
        return user
