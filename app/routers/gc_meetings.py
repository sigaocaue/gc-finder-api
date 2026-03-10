"""Router de reuniões do GC — horários de encontro vinculados a um GC."""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.dependencies import CurrentUser, DbSession
from app.schemas.common import ApiResponse
from app.schemas.gc_meeting import GcMeetingCreate, GcMeetingResponse, GcMeetingUpdate
from app.services.gc_service import GcService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gcs/{gc_id}/meetings", tags=["reuniões"])


# --- Rota pública ---


@router.get("/", response_model=ApiResponse[list[GcMeetingResponse]])
async def list_meetings(gc_id: UUID, db: DbSession):
    """Lista todas as reuniões de um GC (rota pública)."""
    service = GcService(db)
    meetings = await service.list_meetings(gc_id)
    return ApiResponse(
        data=[GcMeetingResponse.model_validate(m) for m in meetings],
        message="Lista de reuniões",
    )


# --- Rotas autenticadas ---


@router.post("/", response_model=ApiResponse[GcMeetingResponse], status_code=status.HTTP_201_CREATED)
async def create_meeting(gc_id: UUID, body: GcMeetingCreate, current_user: CurrentUser, db: DbSession):
    """Cria um novo horário de reunião para o GC (requer autenticação)."""
    service = GcService(db)
    meeting = await service.create_meeting(gc_id, body)
    return ApiResponse(
        data=GcMeetingResponse.model_validate(meeting),
        message="Reunião criada com sucesso",
    )


@router.put("/{meeting_id}", response_model=ApiResponse[GcMeetingResponse])
async def update_meeting(
    gc_id: UUID,
    meeting_id: UUID,
    body: GcMeetingUpdate,
    current_user: CurrentUser,
    db: DbSession,
):
    """Atualiza um horário de reunião (requer autenticação)."""
    service = GcService(db)
    meeting = await service.update_meeting(gc_id, meeting_id, body)
    return ApiResponse(
        data=GcMeetingResponse.model_validate(meeting),
        message="Reunião atualizada com sucesso",
    )


@router.delete("/{meeting_id}", response_model=ApiResponse)
async def delete_meeting(gc_id: UUID, meeting_id: UUID, current_user: CurrentUser, db: DbSession):
    """Remove uma reunião do GC (requer autenticação)."""
    service = GcService(db)
    await service.delete_meeting(gc_id, meeting_id)
    return ApiResponse(message="Reunião removida com sucesso")
