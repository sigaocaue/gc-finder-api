"""Schemas de líder para criação, atualização e resposta."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LeaderContactCreate(BaseModel):
    """Dados para criação de um contato do líder."""

    type: str
    value: str
    label: str | None = None


class LeaderContactUpdate(BaseModel):
    """Dados para atualização parcial de um contato do líder."""

    type: str | None = None
    value: str | None = None
    label: str | None = None


class LeaderContactResponse(BaseModel):
    """Dados do contato do líder retornados pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    value: str
    label: str | None = None
    created_at: datetime


class LeaderCreate(BaseModel):
    """Dados para criação de um novo líder."""

    name: str
    bio: str | None = None
    photo_url: str | None = None
    contacts: list[LeaderContactCreate] = []


class LeaderUpdate(BaseModel):
    """Dados para atualização parcial de um líder."""

    name: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    is_active: bool | None = None


class LeaderResponse(BaseModel):
    """Dados completos do líder retornados pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    display_name: str | None = None
    bio: str | None = None
    photo_url: str | None = None
    is_active: bool
    contacts: list[LeaderContactResponse] = []
    created_at: datetime


class LeaderBrief(BaseModel):
    """Resumo do líder para exibição no detalhe do GC."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    contacts: list[LeaderContactResponse] = []
