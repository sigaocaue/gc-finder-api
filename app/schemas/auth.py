"""Schemas de autenticação: login, tokens e refresh."""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Dados de login do usuário."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Resposta com tokens de acesso e refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Requisição para renovação de token."""

    refresh_token: str


class LogoutRequest(BaseModel):
    """Requisição para logout (revogação do refresh token)."""

    refresh_token: str
