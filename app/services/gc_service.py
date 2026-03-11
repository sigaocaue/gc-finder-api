"""Serviço de gerenciamento de GCs (Grupos de Convivência)."""

import logging
from datetime import time
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gc import Gc
from app.models.gc_leader import GcLeader
from app.models.gc_media import GcMedia
from app.models.gc_meeting import GcMeeting
from app.schemas.gc import GcCreate, GcUpdate
from app.schemas.gc_media import GcMediaCreate, GcMediaUpdate
from app.schemas.gc_meeting import GcMeetingCreate, GcMeetingUpdate
from app.services.geocoding_service import (
    fetch_address_from_cep,
    fetch_coordinates,
    haversine_distance,
)
from app.utils.cep import sanitize_cep

logger = logging.getLogger(__name__)


class GcService:
    """Serviço responsável pelas operações de negócio dos GCs."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------ #
    # CRUD principal de GC
    # ------------------------------------------------------------------ #

    async def list_all(self, skip: int = 0, limit: int = 100) -> list[Gc]:
        """Retorna GCs ativos com paginação."""
        result = await self.db.execute(
            select(Gc).where(Gc.is_active.is_(True)).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id(self, gc_id: UUID) -> Gc:
        """Busca um GC pelo ID. Levanta 404 se não encontrado."""
        result = await self.db.execute(select(Gc).where(Gc.id == gc_id))
        gc = result.scalars().first()
        if gc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="GC não encontrado",
            )
        return gc

    async def create(self, data: GcCreate) -> Gc:
        """Cria um novo GC. Consulta o CEP para preencher endereço e coordenadas."""
        # Monta o endereço completo para geocodificação
        full_address = (
            f"{data.street}, {data.number or 's/n'}, "
            f"{data.neighborhood}, {data.city} - "
            f"{data.state}, Brasil"
        )
        coords = await fetch_coordinates(full_address)

        gc = Gc(
            name=data.name,
            description=data.description,
            zip_code=sanitize_cep(data.zip_code),
            street=data.street,
            number=data.number,
            complement=data.complement,
            neighborhood=data.neighborhood,
            city=data.city,
            state=data.state,
            latitude=coords[0] if coords else None,
            longitude=coords[1] if coords else None,
            is_active=True,
        )
        self.db.add(gc)
        await self.db.flush()

        # Vincula líderes informados ao GC
        for leader_id_str in data.leaders:
            leader_id = UUID(leader_id_str)
            link = GcLeader(gc_id=gc.id, leader_id=leader_id)
            self.db.add(link)

        # Cria reuniões informadas e vincula ao GC
        for meeting_data in data.meetings:
            hour, minute = map(int, meeting_data.start_time.split(":"))
            meeting = GcMeeting(
                gc_id=gc.id,
                weekday=meeting_data.weekday,
                start_time=time(hour, minute),
                notes=meeting_data.notes,
            )
            self.db.add(meeting)

        # Cria mídias informadas e vincula ao GC
        for media_data in data.medias:
            media = GcMedia(
                gc_id=gc.id,
                type=media_data.type,
                url=media_data.url,
                caption=media_data.caption,
                display_order=media_data.display_order,
            )
            self.db.add(media)

        await self.db.commit()
        await self.db.refresh(gc)
        logger.info("GC criado: %s (id=%s)", gc.name, gc.id)
        return gc

    async def update(self, gc_id: UUID, data: GcUpdate) -> Gc:
        """Atualiza os dados de um GC existente."""
        gc = await self.get_by_id(gc_id)
        update_data = data.model_dump(exclude_unset=True)

        # Extrai os campos de relacionamento antes de iterar nos campos simples
        leaders_input = update_data.pop("leaders", None)
        meetings_input = update_data.pop("meetings", None)
        medias_input = update_data.pop("medias", None)

        # Se campos de endereço foram alterados, recalcula coordenadas
        if "zip_code" in update_data:
            update_data["zip_code"] = sanitize_cep(update_data["zip_code"])

            full_address = (
                f"{update_data['street']}, {update_data.get('number', gc.number) or 's/n'}, "
                f"{update_data['neighborhood']}, {update_data['city']} - "
                f"{update_data['state']}, Brasil"
            )
            coords = await fetch_coordinates(full_address)
            update_data["latitude"] = coords[0] if coords else None
            update_data["longitude"] = coords[1] if coords else None

        for field, value in update_data.items():
            setattr(gc, field, value)

        # Atualiza líderes se o campo foi enviado (None = não altera)
        if leaders_input is not None:
            existing_leaders = await self.db.execute(
                select(GcLeader).where(GcLeader.gc_id == gc_id)
            )
            for link in existing_leaders.scalars().all():
                await self.db.delete(link)

            for leader_id_str in leaders_input:
                leader_id = UUID(leader_id_str)
                link = GcLeader(gc_id=gc_id, leader_id=leader_id)
                self.db.add(link)

        # Atualiza reuniões se o campo foi enviado (None = não altera)
        if meetings_input is not None:
            existing_meetings = await self.db.execute(
                select(GcMeeting).where(GcMeeting.gc_id == gc_id)
            )
            for meeting in existing_meetings.scalars().all():
                await self.db.delete(meeting)

            for meeting_data in meetings_input:
                hour, minute = map(int, meeting_data["start_time"].split(":"))
                meeting = GcMeeting(
                    gc_id=gc_id,
                    weekday=meeting_data["weekday"],
                    start_time=time(hour, minute),
                    notes=meeting_data.get("notes"),
                )
                self.db.add(meeting)

        # Atualiza mídias se o campo foi enviado (None = não altera)
        if medias_input is not None:
            existing_medias = await self.db.execute(
                select(GcMedia).where(GcMedia.gc_id == gc_id)
            )
            for media in existing_medias.scalars().all():
                await self.db.delete(media)

            for media_data in medias_input:
                media = GcMedia(
                    gc_id=gc_id,
                    type=media_data["type"],
                    url=media_data["url"],
                    caption=media_data.get("caption"),
                    display_order=media_data.get("display_order", 0),
                )
                self.db.add(media)

        await self.db.commit()
        await self.db.refresh(gc)
        logger.info("GC atualizado: id=%s", gc.id)
        return gc

    async def deactivate(self, gc_id: UUID) -> Gc:
        """Desativa um GC (soft delete)."""
        gc = await self.get_by_id(gc_id)
        gc.is_active = False
        await self.db.commit()
        await self.db.refresh(gc)
        logger.info("GC desativado: id=%s", gc.id)
        return gc

    # ------------------------------------------------------------------ #
    # Vínculo GC ↔ Líder
    # ------------------------------------------------------------------ #

    async def link_leader(
        self, gc_id: UUID, leader_id: UUID, is_primary: bool = False
    ) -> None:
        """Vincula um líder a um GC."""
        # Verifica se o GC existe
        await self.get_by_id(gc_id)

        # Verifica se o vínculo já existe
        result = await self.db.execute(
            select(GcLeader).where(
                GcLeader.gc_id == gc_id, GcLeader.leader_id == leader_id
            )
        )
        existing = result.scalars().first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Líder já vinculado a este GC",
            )

        link = GcLeader(gc_id=gc_id, leader_id=leader_id)
        self.db.add(link)
        await self.db.commit()
        logger.info("Líder %s vinculado ao GC %s", leader_id, gc_id)

    async def unlink_leader(self, gc_id: UUID, leader_id: UUID) -> None:
        """Remove o vínculo de um líder com um GC."""
        result = await self.db.execute(
            select(GcLeader).where(
                GcLeader.gc_id == gc_id, GcLeader.leader_id == leader_id
            )
        )
        link = result.scalars().first()
        if link is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vínculo entre líder e GC não encontrado",
            )

        await self.db.delete(link)
        await self.db.commit()
        logger.info("Líder %s desvinculado do GC %s", leader_id, gc_id)

    # ------------------------------------------------------------------ #
    # Mapa e busca por proximidade
    # ------------------------------------------------------------------ #

    async def get_map_data(self) -> list[Gc]:
        """Retorna todos os GCs ativos que possuem coordenadas geográficas."""
        result = await self.db.execute(
            select(Gc).where(
                Gc.is_active.is_(True),
                Gc.latitude.isnot(None),
                Gc.longitude.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def find_nearby(self, zip_code: str) -> list[dict]:
        """Encontra os GCs mais próximos de um CEP informado.

        Transforma o CEP de entrada coordenadas geográficas de latitude e longitude,
        depois calcula a distância Haversine até
        todos os GCs ativos com coordenadas e retorna ordenado por distância.
        """
        # Busca endereço e coordenadas do CEP informado
        address_data = await fetch_address_from_cep(zip_code)
        full_address = (
            f"{address_data['street']}, {address_data['neighborhood']}, "
            f"{address_data['city']} - {address_data['state']}, Brasil"
        )
        coords = await fetch_coordinates(full_address)
        if coords is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível geocodificar o CEP informado",
            )

        user_lat, user_lng = coords

        # Busca todos os GCs ativos com coordenadas
        gcs = await self.get_map_data()

        # Calcula a distância para cada GC
        nearby = []
        for gc in gcs:
            dist = haversine_distance(
                user_lat, user_lng, float(gc.latitude), float(gc.longitude)
            )
            nearby.append(
                {
                    "id": gc.id,
                    "name": gc.name,
                    "latitude": float(gc.latitude),
                    "longitude": float(gc.longitude),
                    "neighborhood": gc.neighborhood,
                    "city": gc.city,
                    "distance_km": round(dist, 2),
                }
            )

        # Ordena por distância
        nearby.sort(key=lambda x: x["distance_km"])
        return nearby

    # ------------------------------------------------------------------ #
    # CRUD de reuniões (meetings)
    # ------------------------------------------------------------------ #

    async def list_meetings(self, gc_id: UUID) -> list[GcMeeting]:
        """Lista todas as reuniões de um GC."""
        await self.get_by_id(gc_id)  # Garante que o GC existe
        result = await self.db.execute(
            select(GcMeeting).where(GcMeeting.gc_id == gc_id)
        )
        return list(result.scalars().all())

    async def create_meeting(self, gc_id: UUID, data: GcMeetingCreate) -> GcMeeting:
        """Cria uma nova reunião para um GC."""
        await self.get_by_id(gc_id)

        # Converte string HH:MM para objeto time
        hour, minute = map(int, data.start_time.split(":"))
        start_time = time(hour, minute)

        meeting = GcMeeting(
            gc_id=gc_id,
            weekday=data.weekday,
            start_time=start_time,
            notes=data.notes,
        )
        self.db.add(meeting)
        await self.db.commit()
        await self.db.refresh(meeting)
        logger.info("Reunião criada para o GC %s: id=%s", gc_id, meeting.id)
        return meeting

    async def update_meeting(
        self, gc_id: UUID, meeting_id: UUID, data: GcMeetingUpdate
    ) -> GcMeeting:
        """Atualiza uma reunião existente de um GC."""
        meeting = await self._get_meeting(gc_id, meeting_id)
        update_data = data.model_dump(exclude_unset=True)

        # Converte start_time de string para time se informado
        if "start_time" in update_data and update_data["start_time"]:
            hour, minute = map(int, update_data["start_time"].split(":"))
            update_data["start_time"] = time(hour, minute)

        for field, value in update_data.items():
            setattr(meeting, field, value)

        await self.db.commit()
        await self.db.refresh(meeting)
        logger.info("Reunião atualizada: id=%s (GC %s)", meeting_id, gc_id)
        return meeting

    async def delete_meeting(self, gc_id: UUID, meeting_id: UUID) -> None:
        """Remove uma reunião de um GC."""
        meeting = await self._get_meeting(gc_id, meeting_id)
        await self.db.delete(meeting)
        await self.db.commit()
        logger.info("Reunião removida: id=%s (GC %s)", meeting_id, gc_id)

    async def _get_meeting(self, gc_id: UUID, meeting_id: UUID) -> GcMeeting:
        """Busca uma reunião pelo ID, verificando que pertence ao GC."""
        result = await self.db.execute(
            select(GcMeeting).where(
                GcMeeting.id == meeting_id, GcMeeting.gc_id == gc_id
            )
        )
        meeting = result.scalars().first()
        if meeting is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reunião não encontrada",
            )
        return meeting

    # ------------------------------------------------------------------ #
    # CRUD de mídias
    # ------------------------------------------------------------------ #

    async def list_medias(self, gc_id: UUID) -> list[GcMedia]:
        """Lista todas as mídias de um GC."""
        await self.get_by_id(gc_id)
        result = await self.db.execute(
            select(GcMedia).where(GcMedia.gc_id == gc_id)
        )
        return list(result.scalars().all())

    async def create_media(self, gc_id: UUID, data: GcMediaCreate) -> GcMedia:
        """Cria uma nova mídia para um GC."""
        await self.get_by_id(gc_id)

        media = GcMedia(
            gc_id=gc_id,
            type=data.type,
            url=data.url,
            caption=data.caption,
            display_order=data.display_order,
        )
        self.db.add(media)
        await self.db.commit()
        await self.db.refresh(media)
        logger.info("Mídia criada para o GC %s: id=%s", gc_id, media.id)
        return media

    async def update_media(
        self, gc_id: UUID, media_id: UUID, data: GcMediaUpdate
    ) -> GcMedia:
        """Atualiza uma mídia existente de um GC."""
        media = await self._get_media(gc_id, media_id)
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(media, field, value)

        await self.db.commit()
        await self.db.refresh(media)
        logger.info("Mídia atualizada: id=%s (GC %s)", media_id, gc_id)
        return media

    async def delete_media(self, gc_id: UUID, media_id: UUID) -> None:
        """Remove uma mídia de um GC."""
        media = await self._get_media(gc_id, media_id)
        await self.db.delete(media)
        await self.db.commit()
        logger.info("Mídia removida: id=%s (GC %s)", media_id, gc_id)

    async def _get_media(self, gc_id: UUID, media_id: UUID) -> GcMedia:
        """Busca uma mídia pelo ID, verificando que pertence ao GC."""
        result = await self.db.execute(
            select(GcMedia).where(GcMedia.id == media_id, GcMedia.gc_id == gc_id)
        )
        media = result.scalars().first()
        if media is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Mídia não encontrada",
            )
        return media
