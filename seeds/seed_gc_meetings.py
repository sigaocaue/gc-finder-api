import logging
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gc import Gc
from app.models.gc_meeting import GcMeeting

logger = logging.getLogger(__name__)

# Encontros semanais para cada GC (weekday: 0=Dom, 1=Seg, ..., 6=Sáb)
MEETINGS_CONFIG = [
    {"weekday": 3, "start_time": time(20, 0), "notes": None},          # Quarta 20h
    {"weekday": 2, "start_time": time(19, 30), "notes": None},         # Terça 19h30
    {"weekday": 5, "start_time": time(20, 0), "notes": "quinzenal"},   # Sexta 20h
    {"weekday": 4, "start_time": time(19, 0), "notes": None},          # Quinta 19h
    {"weekday": 6, "start_time": time(16, 0), "notes": None},          # Sábado 16h
]


async def seed_gc_meetings(db: AsyncSession, gcs: list[Gc]) -> None:
    """Cria encontros semanais para cada GC de forma idempotente."""
    for i, gc in enumerate(gcs):
        if i >= len(MEETINGS_CONFIG):
            break

        config = MEETINGS_CONFIG[i]
        result = await db.execute(
            select(GcMeeting).where(
                GcMeeting.gc_id == gc.id,
                GcMeeting.weekday == config["weekday"],
            )
        )
        if result.scalar_one_or_none() is not None:
            logger.info(
                f"Encontro do GC '{gc.name}' (dia {config['weekday']}) já existe, pulando."
            )
            continue

        meeting = GcMeeting(
            gc_id=gc.id,
            weekday=config["weekday"],
            start_time=config["start_time"],
            notes=config["notes"],
        )
        db.add(meeting)
        logger.info(f"Encontro criado para o GC '{gc.name}' (dia {config['weekday']}).")

    await db.commit()
