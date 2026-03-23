"""Router público — endpoints do mapa, busca por proximidade e registro de interesse."""

import logging

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import DbSession
from app.schemas.common import ApiResponse
from app.schemas.gc import GcMapItem, GcNearbyItem
from app.schemas.public import InterestRequest
from app.services.gc_service import GcService
from app.services.google_forms_service import submit_interest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/public", tags=["público"])


@router.get("/gcs/map", response_model=ApiResponse[list[GcMapItem]])
async def gcs_for_map(db: DbSession):
    """Lista todos os GCs ativos com coordenadas para exibição no mapa."""
    service = GcService(db)
    items = await service.get_map_data()
    return ApiResponse(
        data=[GcMapItem.model_validate(item) for item in items],
        message="GCs para o mapa",
    )


@router.get("/gcs/nearby", response_model=ApiResponse[list[GcNearbyItem]])
async def gcs_nearby(
    db: DbSession,
    zip_code: str = Query(..., description="CEP para busca por proximidade"),
):
    """Busca GCs próximos a um CEP informado, ordenados por distância."""
    service = GcService(db)
    items = await service.find_nearby(zip_code)
    return ApiResponse(data=items, message="GCs próximos encontrados")


@router.post("/interest", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def register_interest(body: InterestRequest, db: DbSession):
    """Registra o interesse de um visitante e envia os dados ao Google Forms."""
    success = await submit_interest(
        name=body.name,
        email=body.email,
        phone=body.phone,
        zip_code=body.zip_code,
        message=body.message,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao enviar dados para o formulário",
        )
    return ApiResponse(message="Interesse registrado com sucesso")
