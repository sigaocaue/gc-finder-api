"""Serviço de gerenciamento de líderes."""

import logging

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leader import Leader
from app.repositories.leader_repository import LeaderRepository
from app.schemas.leader import LeaderCreate, LeaderUpdate

logger = logging.getLogger(__name__)


class LeaderService:
    """Serviço responsável pelas operações de negócio de líderes."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = LeaderRepository(db)

    async def list_all(self) -> list[Leader]:
        """Retorna todos os líderes ativos."""
        return await self.repo.get_all_active()

    async def get_by_id(self, leader_id) -> Leader:
        """Busca um líder pelo ID. Levanta 404 se não encontrado."""
        leader = await self.repo.get_by_id(leader_id)
        if leader is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Líder não encontrado",
            )
        return leader

    async def create(self, data: LeaderCreate) -> Leader:
        """Cria um novo líder."""
        leader = Leader(**data.model_dump())
        leader = await self.repo.create(leader)
        logger.info("Líder criado: %s (id=%s)", leader.name, leader.id)
        return leader

    async def update(self, leader_id, data: LeaderUpdate) -> Leader:
        """Atualiza os dados de um líder existente."""
        leader = await self.get_by_id(leader_id)

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(leader, field, value)

        leader = await self.repo.update(leader)
        logger.info("Líder atualizado: id=%s", leader.id)
        return leader

    async def deactivate(self, leader_id) -> Leader:
        """Desativa um líder (soft delete)."""
        leader = await self.get_by_id(leader_id)
        leader = await self.repo.deactivate(leader)
        logger.info("Líder desativado: id=%s", leader.id)
        return leader
