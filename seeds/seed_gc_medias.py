import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gc import Gc
from app.models.gc_media import GcMedia

logger = logging.getLogger(__name__)


async def seed_gc_medias(db: AsyncSession, gcs: list[Gc]) -> None:
    """Cria mídias de exemplo para os GCs de forma idempotente."""
    for gc in gcs:
        result = await db.execute(
            select(GcMedia).where(GcMedia.gc_id == gc.id)
        )
        if result.scalars().first() is not None:
            logger.info(f"Mídias do GC '{gc.name}' já existem, pulando.")
            continue

        media = GcMedia(
            gc_id=gc.id,
            type="image",
            url=f"https://placehold.co/600x400?text={gc.name.replace(' ', '+')}",
            caption=f"Foto do {gc.name}",
            display_order=0,
        )
        db.add(media)
        logger.info(f"Mídia criada para o GC '{gc.name}'.")

    await db.commit()
