"""Schemas de usuário para criação, atualização e resposta."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    """Dados para criação de um novo usuário."""

    name: str
    email: EmailStr
    password: str
    role: str = "editor"


class UserUpdate(BaseModel):
    """Dados para atualização parcial de um usuário."""

    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """Dados do usuário retornados pela API (sem password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
