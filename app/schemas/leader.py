"""Schemas de líder para criação, atualização e resposta."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LeaderCreate(BaseModel):
    """Dados para criação de um novo líder."""

    name: str
    whatsapp: str | None = None
    instagram: str | None = None
    email: str | None = None
    bio: str | None = None
    photo_url: str | None = None


class LeaderUpdate(BaseModel):
    """Dados para atualização parcial de um líder."""

    name: str | None = None
    whatsapp: str | None = None
    instagram: str | None = None
    email: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    is_active: bool | None = None


class LeaderResponse(BaseModel):
    """Dados completos do líder retornados pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    whatsapp: str | None = None
    instagram: str | None = None
    email: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    is_active: bool
    created_at: datetime


class LeaderBrief(BaseModel):
    """Resumo do líder para exibição no detalhe do GC."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    whatsapp: str | None = None
    instagram: str | None = None
    is_primary: bool
