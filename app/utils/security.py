"""Utilitários de segurança: hashing de senhas, criação e decodificação de tokens JWT."""

import hashlib
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# Contexto de hashing de senhas usando bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Gera o hash bcrypt de uma senha em texto plano."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica se a senha em texto plano corresponde ao hash armazenado."""
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    """Cria um token JWT de acesso com expiração configurada."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_expire_minutes
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_access_secret, algorithm="HS256")


def create_refresh_token(data: dict) -> str:
    """Cria um token JWT de refresh com expiração configurada."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.jwt_refresh_expire_days
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_refresh_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    """Decodifica um token de acesso. Retorna o payload ou None em caso de erro."""
    try:
        return jwt.decode(token, settings.jwt_access_secret, algorithms=["HS256"])
    except JWTError:
        return None


def decode_refresh_token(token: str) -> dict | None:
    """Decodifica um token de refresh. Retorna o payload ou None em caso de erro."""
    try:
        return jwt.decode(token, settings.jwt_refresh_secret, algorithms=["HS256"])
    except JWTError:
        return None


def hash_token(token: str) -> str:
    """Gera hash SHA-256 de um token para armazenamento seguro."""
    return hashlib.sha256(token.encode()).hexdigest()
