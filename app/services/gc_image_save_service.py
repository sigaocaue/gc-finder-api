"""Serviço de salvamento de GC importado — cadastra GC, líderes, contatos e encontros."""

import logging
from datetime import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.gc import Gc
from app.models.gc_leader import GcLeader
from app.models.gc_meeting import GcMeeting
from app.models.leader import Leader
from app.models.leader_contact import LeaderContact
from app.schemas.gc_image_import import GcImportSaveRequest
from app.services.geocoding_service import fetch_coordinates

logger = logging.getLogger(__name__)


class GcImageSaveService:
    """Cadastra um GC completo a partir dos dados extraídos (e possivelmente revisados)."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def save(self, data: GcImportSaveRequest) -> Gc:
        """Cria GC, líderes, contatos e encontros no banco."""

        # --- Geocoding se lat/lng/zip_code forem nulos ---
        latitude = data.latitude
        longitude = data.longitude
        zip_code = data.zip_code
        city = data.city
        state = data.state

        if latitude is None or longitude is None or zip_code is None:
            full_address = (
                f"{data.street}, {data.number or 's/n'}, "
                f"{data.neighborhood or ''}, {data.city} - "
                f"{data.state}, Brasil"
            )
            logger.info("[geocoding] Query: \"%s\"", full_address)
            coords = await fetch_coordinates(full_address)
            if coords:
                latitude = latitude or coords[0]
                longitude = longitude or coords[1]
                logger.info(
                    "[geocoding] Resultado: lat=%s, lng=%s", coords[0], coords[1]
                )
            else:
                logger.warning(
                    "[geocoding] Falha no geocoding — salvando sem coordenadas"
                )

        # --- Criar GC ---
        gc = Gc(
            name=data.name,
            description=data.description,
            zip_code=zip_code or "",
            street=data.street,
            number=data.number,
            complement=data.complement,
            neighborhood=data.neighborhood or "",
            city=city,
            state=state,
            latitude=latitude,
            longitude=longitude,
            is_active=True,
        )
        self.db.add(gc)
        await self.db.flush()

        # --- Criar líderes e contatos ---
        for idx, leader_data in enumerate(data.leaders):
            # Busca líder existente por nome (case-insensitive)
            result = await self.db.execute(
                select(Leader).where(
                    func.lower(Leader.name) == leader_data.name.lower()
                )
            )
            leader = result.scalars().first()

            if leader is None:
                leader = Leader(name=leader_data.name, is_active=True)
                self.db.add(leader)
                await self.db.flush()

            # Cria contatos do líder
            for contact_data in leader_data.contacts:
                contact = LeaderContact(
                    leader_id=leader.id,
                    type=contact_data.type,
                    value=contact_data.value,
                    label=contact_data.label,
                )
                self.db.add(contact)

            # Vincula líder ao GC
            link = GcLeader(gc_id=gc.id, leader_id=leader.id)
            self.db.add(link)

        # --- Criar encontros ---
        for meeting_data in data.meetings:
            hour, minute = map(int, meeting_data.start_time.split(":"))
            meeting = GcMeeting(
                gc_id=gc.id,
                weekday=meeting_data.weekday,
                start_time=time(hour, minute),
                notes=meeting_data.notes,
            )
            self.db.add(meeting)

        await self.db.commit()

        # Recarrega o GC com todas as relações
        result = await self.db.execute(
            select(Gc)
            .where(Gc.id == gc.id)
            .options(
                selectinload(Gc.leader_associations)
                .selectinload(GcLeader.leader)
                .selectinload(Leader.contacts),
                selectinload(Gc.meetings),
                selectinload(Gc.medias),
            )
        )
        gc = result.scalars().first()

        logger.info('[gc_image_save] GC "%s" cadastrado — id=%s', gc.name, gc.id)
        return gc
