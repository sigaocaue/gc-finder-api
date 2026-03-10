"""
Script principal para executar todos os seeds em ordem.

Uso: python -m seeds.run_seeds
"""

import asyncio
import logging
import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para importar o app
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import async_session
from app.logging_config import setup_logging
from seeds.seed_gc_medias import seed_gc_medias
from seeds.seed_gc_meetings import seed_gc_meetings
from seeds.seed_gcs import seed_gcs
from seeds.seed_leaders import seed_leaders
from seeds.seed_users import seed_users

logger = logging.getLogger(__name__)


async def run_all_seeds() -> None:
    """Executa todos os seeds na ordem correta."""
    setup_logging()
    logger.info("Iniciando execução dos seeds...")

    async with async_session() as db:
        logger.info("--- Seed: Usuários ---")
        await seed_users(db)

        logger.info("--- Seed: Líderes ---")
        leaders = await seed_leaders(db)

        logger.info("--- Seed: GCs ---")
        gcs = await seed_gcs(db, leaders)

        logger.info("--- Seed: Encontros ---")
        await seed_gc_meetings(db, gcs)

        logger.info("--- Seed: Mídias ---")
        await seed_gc_medias(db, gcs)

    logger.info("Todos os seeds foram executados com sucesso!")


if __name__ == "__main__":
    asyncio.run(run_all_seeds())
