"""Router de health check — verifica se a API e o banco estão operacionais."""

import logging

from fastapi import APIRouter
from sqlalchemy import text

from app.dependencies import DbSession
from app.schemas.common import ApiResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=ApiResponse[dict])
async def health_check(db: DbSession):
    """Verifica a conexão com o banco de dados e retorna o status da API."""
    try:
        await db.execute(text("SELECT 1"))
        return ApiResponse(
            data={"status": "healthy", "database": "connected"},
            message="API operacional",
        )
    except Exception as exc:
        logger.error("Falha no health check: %s", exc)
        return ApiResponse(
            data={"status": "unhealthy", "database": "disconnected"},
            message="Falha na conexão com o banco de dados",
        )
