"""Router de estatísticas — retorna a contagem de registros por entidade."""

import logging

from fastapi import APIRouter
from sqlalchemy import func, select

from app.dependencies import AdminUser, DbSession
from app.models import Gc, GcMedia, GcMeeting, Leader, LeaderContact, User
from app.schemas.common import ApiResponse
from app.schemas.stats import EntityCountsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("/counts", response_model=ApiResponse[EntityCountsResponse])
async def get_entity_counts(db: DbSession, current_user: AdminUser) -> ApiResponse[EntityCountsResponse]:
    """Retorna a quantidade de registros ativos de cada entidade principal."""
    # Entidades com soft delete (is_active) — conta apenas registros ativos
    soft_delete_models = {
        "users": User,
        "leaders": Leader,
        "gcs": Gc,
    }

    # Entidades sem soft delete — conta todos os registros
    regular_models = {
        "meetings": GcMeeting,
        "medias": GcMedia,
        "leader_contacts": LeaderContact,
    }

    counts: dict[str, int] = {}

    for name, model in soft_delete_models.items():
        result = await db.execute(
            select(func.count()).select_from(model).where(model.is_active.is_(True))
        )
        counts[name] = result.scalar_one()

    for name, model in regular_models.items():
        result = await db.execute(
            select(func.count()).select_from(model)
        )
        counts[name] = result.scalar_one()

    logger.info("Contagem de entidades consultada pelo usuário %s", current_user.email)

    return ApiResponse(
        data=EntityCountsResponse(**counts),
        message="Contagem de registros por entidade",
    )
