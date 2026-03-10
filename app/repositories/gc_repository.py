"""Repositório de operações de banco de dados para GCs."""

from uuid import UUID

from sqlalchemy import select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.gc import Gc
from app.models.gc_leader import GcLeader
from app.models.gc_media import GcMedia
from app.models.gc_meeting import GcMeeting


class GcRepository:
    """Repositório para gerenciamento de GCs no banco de dados."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── GC ────────────────────────────────────────────────────────────

    async def get_by_id(self, gc_id: UUID) -> Gc | None:
        """Busca um GC pelo ID com carregamento antecipado de líderes, reuniões e mídias."""
        result = await self.db.execute(
            select(Gc)
            .where(Gc.id == gc_id)
            .options(
                selectinload(Gc.leader_associations).selectinload(GcLeader.leader),
                selectinload(Gc.meetings),
                selectinload(Gc.medias),
            )
        )
        return result.scalars().first()

    async def get_all_active(self, skip: int = 0, limit: int = 100) -> list[Gc]:
        """Retorna todos os GCs ativos com paginação."""
        result = await self.db.execute(
            select(Gc)
            .where(Gc.is_active.is_(True))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_active_with_coords(self) -> list[Gc]:
        """Retorna todos os GCs ativos que possuem coordenadas geográficas."""
        result = await self.db.execute(
            select(Gc).where(
                Gc.is_active.is_(True),
                Gc.latitude.isnot(None),
                Gc.longitude.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def create(self, gc: Gc) -> Gc:
        """Cria um novo GC no banco de dados."""
        self.db.add(gc)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(gc)
        return gc

    async def update(self, gc: Gc) -> Gc:
        """Atualiza os dados de um GC existente."""
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(gc)
        return gc

    async def deactivate(self, gc: Gc) -> Gc:
        """Desativa um GC (soft delete)."""
        gc.is_active = False
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(gc)
        return gc

    # ── Líderes do GC ────────────────────────────────────────────────

    async def add_leader(
        self, gc_id: UUID, leader_id: UUID, is_primary: bool = False
    ) -> None:
        """Associa um líder a um GC na tabela pivot gc_leaders."""
        gc_leader = GcLeader(
            gc_id=gc_id, leader_id=leader_id, is_primary=is_primary
        )
        self.db.add(gc_leader)
        await self.db.flush()
        await self.db.commit()

    async def remove_leader(self, gc_id: UUID, leader_id: UUID) -> None:
        """Remove a associação de um líder com um GC."""
        await self.db.execute(
            sa_delete(GcLeader).where(
                GcLeader.gc_id == gc_id,
                GcLeader.leader_id == leader_id,
            )
        )
        await self.db.commit()

    # ── Reuniões do GC ───────────────────────────────────────────────

    async def get_meetings(self, gc_id: UUID) -> list[GcMeeting]:
        """Retorna todas as reuniões de um GC."""
        result = await self.db.execute(
            select(GcMeeting).where(GcMeeting.gc_id == gc_id)
        )
        return list(result.scalars().all())

    async def get_meeting_by_id(self, meeting_id: UUID) -> GcMeeting | None:
        """Busca uma reunião pelo ID."""
        result = await self.db.execute(
            select(GcMeeting).where(GcMeeting.id == meeting_id)
        )
        return result.scalars().first()

    async def create_meeting(self, meeting: GcMeeting) -> GcMeeting:
        """Cria uma nova reunião para um GC."""
        self.db.add(meeting)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def update_meeting(self, meeting: GcMeeting) -> GcMeeting:
        """Atualiza os dados de uma reunião existente."""
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(meeting)
        return meeting

    async def delete_meeting(self, meeting: GcMeeting) -> None:
        """Remove uma reunião do banco de dados."""
        await self.db.delete(meeting)
        await self.db.commit()

    # ── Mídias do GC ─────────────────────────────────────────────────

    async def get_medias(self, gc_id: UUID) -> list[GcMedia]:
        """Retorna todas as mídias de um GC."""
        result = await self.db.execute(
            select(GcMedia).where(GcMedia.gc_id == gc_id)
        )
        return list(result.scalars().all())

    async def get_media_by_id(self, media_id: UUID) -> GcMedia | None:
        """Busca uma mídia pelo ID."""
        result = await self.db.execute(
            select(GcMedia).where(GcMedia.id == media_id)
        )
        return result.scalars().first()

    async def create_media(self, media: GcMedia) -> GcMedia:
        """Cria uma nova mídia para um GC."""
        self.db.add(media)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(media)
        return media

    async def update_media(self, media: GcMedia) -> GcMedia:
        """Atualiza os dados de uma mídia existente."""
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(media)
        return media

    async def delete_media(self, media: GcMedia) -> None:
        """Remove uma mídia do banco de dados."""
        await self.db.delete(media)
        await self.db.commit()
