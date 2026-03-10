import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leader import Leader

logger = logging.getLogger(__name__)

LEADERS = [
    {
        "name": "João Silva",
        "whatsapp": "11999990001",
        "instagram": "@joaosilva",
        "email": "joao.silva@email.com",
        "bio": "Líder de GC há 5 anos, apaixonado por servir.",
    },
    {
        "name": "Maria Oliveira",
        "whatsapp": "11999990002",
        "instagram": "@mariaoliveira",
        "email": "maria.oliveira@email.com",
        "bio": "Líder do GC Colônia, serve com alegria.",
    },
    {
        "name": "Pedro Santos",
        "whatsapp": "11999990003",
        "instagram": "@pedrosantos",
        "email": "pedro.santos@email.com",
        "bio": "Líder e músico, ama receber pessoas em casa.",
    },
    {
        "name": "Ana Costa",
        "whatsapp": "11999990004",
        "instagram": "@anacosta",
        "email": "ana.costa@email.com",
        "bio": "Líder de jovens, focada em discipulado.",
    },
    {
        "name": "Lucas Ferreira",
        "whatsapp": "11999990005",
        "instagram": "@lucasferreira",
        "email": "lucas.ferreira@email.com",
        "bio": "Líder de casais, casado há 10 anos.",
    },
]


async def seed_leaders(db: AsyncSession) -> list[Leader]:
    """Cria líderes iniciais de forma idempotente. Retorna a lista de líderes."""
    leaders = []
    for leader_data in LEADERS:
        result = await db.execute(
            select(Leader).where(Leader.name == leader_data["name"])
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            logger.info(f"Líder '{leader_data['name']}' já existe, pulando.")
            leaders.append(existing)
            continue

        leader = Leader(**leader_data)
        db.add(leader)
        leaders.append(leader)
        logger.info(f"Líder '{leader_data['name']}' criado com sucesso.")

    await db.commit()
    for leader in leaders:
        await db.refresh(leader)
    return leaders
