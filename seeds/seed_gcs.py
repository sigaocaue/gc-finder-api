"""Seed centralizado de GCs com líderes, encontros e mídias aninhados."""

import logging
from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gc import Gc
from app.models.gc_leader import GcLeader
from app.models.gc_media import GcMedia
from app.models.gc_meeting import GcMeeting
from app.models.leader import Leader
from app.models.leader_contact import LeaderContact

logger = logging.getLogger(__name__)

# Chaves que não são colunas do modelo Gc
NESTED_KEYS = {"leaders", "meetings", "medias"}

# GCs com endereços reais na região de Jundiaí/SP
GCS = [
    {
        "name": "GC Casais Jardim Samambaias",
        "description": "GC voltado para casais localizado no bairro Jardim Samambaias.",
        "zip_code": "13211502",
        "street": "Rua Carmela Nano",
        "number": "432",
        "neighborhood": "Jardim Samambaias",
        "city": "Jundiaí",
        "state": "SP",
        "latitude": -23.184312,
        "longitude": -46.909713,
        "leaders": [
            {
                "name": "Vanessa",
                "contacts": [
                    {"type": "whatsapp", "value": "11983312401"},
                ],
            },
            {
                "name": "Cadu",
                "contacts": [
                    {"type": "whatsapp", "value": "11983312572"},
                ],
            },
        ],
        "meetings": [
            {"weekday": 5, "start_time": time(20, 0), "notes": None},
        ],
    },
    {
        "name": "GC Casais Colonia",
        "description": "GC voltado para casais localizado no bairro Colonia.",
        "zip_code": "13218392",
        "street": "Rua Névia Sálvia",
        "number": "310",
        "complement": "BLOCO A, APTO 13",
        "neighborhood": "Mirante da Colonia",
        "city": "Jundiaí",
        "state": "SP",
        "latitude": -23.1771617,
        "longitude": -46.8605974,
        "leaders": [
            {
                "name": "Jadiel",
                "contacts": [
                    {"type": "whatsapp", "value": "11971715508"},
                ],
            },
            {
                "name": "Mariane",
                "contacts": [
                    {"type": "whatsapp", "value": "11971790708"},
                ],
            },
        ],
        "meetings": [
            {"weekday": 5, "start_time": time(19, 30), "notes": None},
        ],
    },
    {
        "name": "GC Depois do Sim Medeiros",
        "description": "GC voltado para casais localizado no bairro Medeiros.",
        "zip_code": "13212241",
        "street": "Avenida Francisco Nobre",
        "number": "455",
        "neighborhood": "Medeiros",
        "city": "Jundiaí",
        "state": "SP",
        "latitude": -23.1831173,
        "longitude": -46.988253,
        "leaders": [
            {
                "name": "Larissa",
                "contacts": [
                    {"type": "whatsapp", "value": "19996382434"},
                ],
            },
            {
                "name": "Elyude",
                "contacts": [
                    {"type": "whatsapp", "value": "11972680651"},
                ],
            },
        ],
        "meetings": [
            {"weekday": 4, "start_time": time(19, 30), "notes": None},
        ],
    },
    {
        "name": "GC Depois do Sim Hortolândia",
        "description": "GC voltado para casais localizado no bairro Vila Hortolândia.",
        "zip_code": "13214065",
        "street": "Rua Itirapina",
        "number": "690",
        "complement": "Living Itirapina",
        "neighborhood": "Vila Lacerda",
        "city": "Jundiaí",
        "state": "SP",
        "latitude": -23.1729273,
        "longitude": -46.9089757,
        "leaders": [
            {
                "name": "Maria Eduarda",
                "display_name": "Madu",
                "contacts": [
                    {"type": "whatsapp", "value": "11975330638"},
                ],
            },
            {
                "name": "Leonardo",
                "display_name": "Léo",
                "contacts": [
                    {"type": "whatsapp", "value": "11995926487"},
                ],
            },
        ],
        "meetings": [
            {"weekday": 2, "start_time": time(19, 30), "notes": None},
        ],
    },
    {
        "name": "GC Eloy Chaves",
        "description": "GC localizado no bairro Eloy Chaves.",
        "zip_code": "13212117",
        "street": "Rua Chiara Lubich",
        "number": "371",
        "complement": "Torre Ype Apto 62 Condomínio Atmosphera",
        "neighborhood": "Jardim Ermida",
        "city": "Jundiaí",
        "state": "SP",
        "latitude": -23.1862314,
        "longitude": -46.972951,
        "leaders": [
            {
                "name": "Bruno",
                "contacts": [
                    {"type": "whatsapp", "value": "11933490020"},
                ],
            },
            {
                "name": "Larissa",
                "display_name": "Lari",
                "contacts": [
                    {"type": "whatsapp", "value": "11984588338"},
                ],
            },
        ],
        "meetings": [
            {"weekday": 2, "start_time": time(20, 0), "notes": None},
        ],
    },
]


async def _get_or_create_leader(db: AsyncSession, leader_data: dict) -> Leader:
    """Busca um líder pelo nome ou cria um novo com seus contatos."""
    result = await db.execute(
        select(Leader).where(Leader.name == leader_data["name"])
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    contacts_data = leader_data.get("contacts", [])
    leader = Leader(
        name=leader_data["name"],
        display_name=leader_data.get("display_name"),
    )

    for contact_data in contacts_data:
        contact = LeaderContact(**contact_data, leader=leader)
        db.add(contact)

    db.add(leader)
    logger.info(f"Líder '{leader_data['name']}' criado com sucesso.")
    return leader


async def _ensure_leader_linked(
    db: AsyncSession, gc: Gc, leader_data: dict
) -> None:
    """Garante que o líder existe e está vinculado ao GC."""
    leader = await _get_or_create_leader(db, leader_data)
    await db.flush()

    # Verifica se o vínculo já existe antes de criar
    result = await db.execute(
        select(GcLeader).where(
            GcLeader.gc_id == gc.id,
            GcLeader.leader_id == leader.id,
        )
    )
    existing_link = result.scalar_one_or_none()

    if existing_link is not None:
        logger.info(
            f"Líder '{leader.name}' já vinculado ao GC '{gc.name}', pulando."
        )
        return

    link = GcLeader(gc_id=gc.id, leader_id=leader.id)
    db.add(link)
    logger.info(f"Líder '{leader.name}' vinculado ao GC '{gc.name}'.")


async def seed_gcs(db: AsyncSession) -> list[Gc]:
    """Cria GCs com líderes, encontros e mídias de forma idempotente."""
    gcs = []

    for gc_entry in GCS:
        gc_name = gc_entry["name"]

        # Separa dados aninhados das colunas do modelo Gc
        leaders_data = gc_entry.get("leaders", [])
        meetings_data = gc_entry.get("meetings", [])
        medias_data = gc_entry.get("medias", [])
        gc_columns = {k: v for k, v in gc_entry.items() if k not in NESTED_KEYS}

        result = await db.execute(select(Gc).where(Gc.name == gc_name))
        gc = result.scalar_one_or_none()

        if gc is not None:
            logger.info(f"GC '{gc_name}' já existe, validando líderes.")
        else:
            gc = Gc(**gc_columns)
            db.add(gc)
            await db.flush()

            # Cria encontros do GC
            for meeting_data in meetings_data:
                meeting = GcMeeting(gc_id=gc.id, **meeting_data)
                db.add(meeting)
                logger.info(
                    f"Encontro criado para o GC '{gc_name}' "
                    f"(dia {meeting_data['weekday']})."
                )

            # Cria mídias do GC
            for media_data in medias_data:
                media = GcMedia(gc_id=gc.id, **media_data)
                db.add(media)
                logger.info(f"Mídia criada para o GC '{gc_name}'.")

            logger.info(f"GC '{gc_name}' criado com sucesso.")

        # Sempre valida e vincula líderes, mesmo para GCs já existentes
        for leader_data in leaders_data:
            await _ensure_leader_linked(db, gc, leader_data)

        gcs.append(gc)

    await db.commit()
    for gc in gcs:
        await db.refresh(gc)

    return gcs
