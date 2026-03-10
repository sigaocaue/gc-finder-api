"""Repositório de operações de banco de dados para Usuários."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Repositório para gerenciamento de usuários no banco de dados."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Busca um usuário pelo ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().first()

    async def get_by_email(self, email: str) -> User | None:
        """Busca um usuário pelo e-mail."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalars().first()

    async def get_all(self) -> list[User]:
        """Retorna todos os usuários."""
        result = await self.db.execute(select(User))
        return list(result.scalars().all())

    async def create(self, user: User) -> User:
        """Cria um novo usuário no banco de dados."""
        self.db.add(user)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user: User) -> User:
        """Atualiza os dados de um usuário existente."""
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def deactivate(self, user: User) -> User:
        """Desativa um usuário (soft delete)."""
        user.is_active = False
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(user)
        return user
