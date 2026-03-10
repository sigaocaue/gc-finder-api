"""Schemas de mídia do GC (imagens, vídeos, posts do Instagram)."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class GcMediaCreate(BaseModel):
    """Dados para criação de uma mídia do GC."""

    type: Literal["image", "instagram_post", "video"]
    url: str
    caption: str | None = None
    display_order: int = 0


class GcMediaUpdate(BaseModel):
    """Dados para atualização parcial de uma mídia."""

    type: Literal["image", "instagram_post", "video"] | None = None
    url: str | None = None
    caption: str | None = None
    display_order: int | None = None


class GcMediaResponse(BaseModel):
    """Dados da mídia retornados pela API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    gc_id: UUID
    type: str
    url: str
    caption: str | None = None
    display_order: int
    created_at: datetime
