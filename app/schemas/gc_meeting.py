"""Schemas de horário de reunião do GC."""

from datetime import datetime, time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GcMeetingCreate(BaseModel):
    """Dados para criação de um horário de reunião."""

    weekday: int = Field(..., ge=0, le=6, description="Dia da semana (0=segunda, 6=domingo)")
    start_time: str = Field(..., description="Horário de início no formato HH:MM")
    notes: str | None = None


class GcMeetingUpdate(BaseModel):
    """Dados para atualização parcial de um horário de reunião."""

    weekday: int | None = Field(None, ge=0, le=6)
    start_time: str | None = None
    notes: str | None = None


class GcMeetingResponse(BaseModel):
    """Dados do horário de reunião retornados pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gc_id: UUID
    weekday: int
    start_time: str
    notes: str | None = None
    created_at: datetime

    @field_validator("start_time", mode="before")
    def format_start_time(cls, value: str | time) -> str:
        if isinstance(value, time):
            return value.strftime("%H:%M")
        return value
