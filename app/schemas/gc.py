"""Schemas do GC (Grupo de Convivência) para criação, atualização, resposta e mapa."""

from datetime import datetime
from uuid import UUID

import re

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.schemas.gc_media import GcMediaCreate, GcMediaResponse
from app.schemas.gc_meeting import GcMeetingCreate, GcMeetingResponse
from app.schemas.leader import LeaderBrief


def _validate_zip_code(value: str) -> str:
    """Valida que o CEP contém exatamente 8 dígitos numéricos."""
    digits = re.sub(r"\D", "", value)
    if len(digits) != 8:
        raise ValueError("O CEP deve conter exatamente 8 dígitos")
    return digits


class GcCreate(BaseModel):
    """Dados para criação de um novo GC."""

    name: str
    description: str | None = None
    zip_code: str
    street: str
    number: str | None = None
    complement: str | None = None
    neighborhood: str
    city: str
    state: str
    leaders: list[str] = []
    meetings: list[GcMeetingCreate] = []
    medias: list[GcMediaCreate] = []

    @field_validator("zip_code")
    @classmethod
    def validate_zip_code(cls, value: str) -> str:
        return _validate_zip_code(value)


class GcUpdate(BaseModel):
    """Dados para atualização parcial de um GC."""

    name: str | None = None
    description: str | None = None
    zip_code: str | None = None
    street: str | None = None
    number: str | None = None
    complement: str | None = None
    neighborhood: str | None = None
    city: str | None = None
    state: str | None = None
    is_active: bool | None = None
    leaders: list[str] | None = None
    meetings: list[GcMeetingCreate] | None = None
    medias: list[GcMediaCreate] | None = None

    _ADDRESS_FIELDS = {"zip_code", "street", "neighborhood", "city", "state"}

    @field_validator("zip_code")
    @classmethod
    def validate_zip_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _validate_zip_code(value)

    @model_validator(mode="after")
    def validate_address_fields(self) -> "GcUpdate":
        """Se qualquer campo de endereço for enviado, todos são obrigatórios."""
        values = self.model_dump(exclude_unset=True)
        sent = self._ADDRESS_FIELDS & values.keys()
        if sent and sent != self._ADDRESS_FIELDS:
            missing = self._ADDRESS_FIELDS - sent
            raise ValueError(
                f"Ao alterar o endereço, todos os campos são obrigatórios. "
                f"Faltando: {', '.join(sorted(missing))}"
            )
        return self


class GcResponse(BaseModel):
    """Dados completos do GC retornados pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None = None
    zip_code: str
    street: str
    number: str | None = None
    complement: str | None = None
    neighborhood: str
    city: str
    state: str
    latitude: float | None = None
    longitude: float | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

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
