"""Repositório de operações de banco de dados para Líderes."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leader import Leader


class LeaderRepository:
    """Repositório para gerenciamento de líderes no banco de dados."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, leader_id: UUID) -> Leader | None:
        """Busca um líder pelo ID."""
        result = await self.db.execute(
            select(Leader).where(Leader.id == leader_id)
        )
        return result.scalars().first()

    async def get_all_active(self) -> list[Leader]:
        """Retorna todos os líderes ativos."""
        result = await self.db.execute(
            select(Leader).where(Leader.is_active.is_(True))
        )
        return list(result.scalars().all())

    async def create(self, leader: Leader) -> Leader:
        """Cria um novo líder no banco de dados."""
        self.db.add(leader)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(leader)
        return leader

    async def update(self, leader: Leader) -> Leader:
        """Atualiza os dados de um líder existente."""
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(leader)
        return leader

    async def deactivate(self, leader: Leader) -> Leader:
        """Desativa um líder (soft delete)."""
        leader.is_active = False
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(leader)
        return leader
