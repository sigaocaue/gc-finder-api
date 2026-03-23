"""Schemas para endpoints públicos."""

from pydantic import BaseModel, EmailStr


class InterestRequest(BaseModel):
    """Dados para registro de interesse em um GC."""

    name: str
    email: EmailStr
    phone: str
    zip_code: str
    message: str | None = None
