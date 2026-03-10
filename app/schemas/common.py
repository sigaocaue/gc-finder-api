"""Schema genérico para respostas padronizadas da API."""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Resposta padrão da API no formato { data, message }."""

    data: T | None = None
    message: str
