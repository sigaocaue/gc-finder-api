"""Schemas do GC (Grupo de Convivência) para criação, atualização, resposta e mapa."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.gc_media import GcMediaResponse
from app.schemas.gc_meeting import GcMeetingResponse
from app.schemas.leader import LeaderBrief


class GcCreate(BaseModel):
    """Dados para criação de um novo GC."""

    name: str
    description: str | None = None
    zip_code: str
    number: str | None = None
    complement: str | None = None


class GcUpdate(BaseModel):
    """Dados para atualização parcial de um GC."""

    name: str | None = None
    description: str | None = None
    zip_code: str | None = None
    number: str | None = None
    complement: str | None = None
    is_active: bool | None = None


class GcResponse(BaseModel):
    """Dados completos do GC retornados pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    zip_code: str
    street: str | None = None
    number: str | None = None
    complement: str | None = None
    neighborhood: str | None = None
    city: str | None = None
    state: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool
    created_at: datetime


class GcDetailResponse(GcResponse):
    """Dados detalhados do GC, incluindo líderes, reuniões e mídias."""

    leaders: list[LeaderBrief] = []
    meetings: list[GcMeetingResponse] = []
    medias: list[GcMediaResponse] = []


class GcMapItem(BaseModel):
    """Dados resumidos do GC para exibição no mapa."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    latitude: float
    longitude: float
    neighborhood: str | None = None
    city: str | None = None


class GcNearbyItem(GcMapItem):
    """Item do mapa com distância calculada em quilômetros."""

    distance_km: float


class GcLeaderLink(BaseModel):
    """Dados para vincular um líder a um GC."""

    leader_id: UUID
    is_primary: bool = False
