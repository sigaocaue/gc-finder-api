import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gc import Gc
from app.models.gc_leader import GcLeader
from app.models.leader import Leader

logger = logging.getLogger(__name__)

# GCs com endereços reais na região de Jundiaí/SP
GCS = [
    {
        "name": "GC Colônia",
        "description": "GC voltado para famílias do bairro Colônia.",
        "zip_code": "13214-070",
        "street": "Rua Zuferey",
        "number": "100",
        "neighborhood": "Colônia",
        "city": "Jundiaí",
        "state": "SP",
        "latitude": -23.1862,
        "longitude": -46.8842,
    },
    {
        "name": "GC Centro",
        "description": "GC no coração de Jundiaí, para quem mora na região central.",
        "zip_code": "13201-000",
        "street": "Rua Barão de Jundiaí",
        "number": "500",
        "neighborhood": "Centro",
        "city": "Jundiaí",
        "state": "SP",
        "latitude": -23.1868,
        "longitude": -46.8847,
    },
    {
        "name": "GC Eloy Chaves",
        "description": "GC para moradores do Eloy Chaves e região.",
        "zip_code": "13212-580",
        "street": "Rua Nelson Tognetti",
        "number": "200",
        "neighborhood": "Jardim Bonfiglioli",
        "city": "Jundiaí",
        "state": "SP",
        "latitude": -23.1575,
        "longitude": -46.8530,
    },
    {
        "name": "GC Itupeva",
        "description": "GC para moradores de Itupeva e região.",
        "zip_code": "13295-000",
        "street": "Rua Cesário Galeno",
        "number": "80",
        "neighborhood": "Centro",
        "city": "Itupeva",
        "state": "SP",
        "latitude": -23.1530,
        "longitude": -47.0577,
    },
    {
        "name": "GC Campo Limpo Paulista",
        "description": "GC para moradores de Campo Limpo Paulista.",
        "zip_code": "13231-610",
        "street": "Rua Alfredo Oliani",
        "number": "150",
        "neighborhood": "Jardim Vitória",
        "city": "Campo Limpo Paulista",
        "state": "SP",
        "latitude": -23.2093,
        "longitude": -46.7870,
    },
]


async def seed_gcs(db: AsyncSession, leaders: list[Leader]) -> list[Gc]:
    """Cria GCs e vincula líderes de forma idempotente."""
    gcs = []
    for i, gc_data in enumerate(GCS):
        result = await db.execute(
            select(Gc).where(Gc.name == gc_data["name"])
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            logger.info(f"GC '{gc_data['name']}' já existe, pulando.")
            gcs.append(existing)
            continue

        gc = Gc(**gc_data)
        db.add(gc)
        gcs.append(gc)
        logger.info(f"GC '{gc_data['name']}' criado com sucesso.")

    await db.commit()
    for gc in gcs:
        await db.refresh(gc)

    # Vincula líderes aos GCs (1 líder por GC, como primário)
    for i, gc in enumerate(gcs):
        if i < len(leaders):
            result = await db.execute(
                select(GcLeader).where(
                    GcLeader.gc_id == gc.id,
                    GcLeader.leader_id == leaders[i].id,
                )
            )
            if result.scalar_one_or_none() is None:
                link = GcLeader(
                    gc_id=gc.id,
                    leader_id=leaders[i].id,
                    is_primary=True,
                )
                db.add(link)
                logger.info(
                    f"Líder '{leaders[i].name}' vinculado ao GC '{gc.name}'."
                )

    await db.commit()
    return gcs
