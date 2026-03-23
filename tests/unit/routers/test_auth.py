"""Unit tests for authentication router endpoints."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.routers import auth
from app.schemas.auth import LoginRequest, RefreshRequest, LogoutRequest


def build_tokens():
    return SimpleNamespace(access_token="token", refresh_token="refresh")


@pytest.mark.asyncio
@patch("app.routers.auth.AuthService")
async def test_login_success(mock_service):
    service = mock_service.return_value
    tokens = build_tokens()
    service.login = AsyncMock(return_value=tokens)

    body = LoginRequest(email="user@example.com", password="secret")
    response = await auth.login(body, db=SimpleNamespace())

    assert response.message == "Login realizado com sucesso"
    assert response.data.access_token == "token"
    service.login.assert_awaited_once_with("user@example.com", "secret")


@pytest.mark.asyncio
@patch("app.routers.auth.AuthService")
async def test_login_failure(mock_service):
    service = mock_service.return_value
    service.login = AsyncMock(return_value=None)

    body = LoginRequest(email="user@example.com", password="wrong")
    with pytest.raises(HTTPException) as excinfo:
        await auth.login(body, db=SimpleNamespace())

    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
@patch("app.routers.auth.AuthService")
async def test_refresh_success(mock_service):
    service = mock_service.return_value
    tokens = build_tokens()
    service.refresh = AsyncMock(return_value=tokens)

    body = RefreshRequest(refresh_token="refresh")
    response = await auth.refresh_token(body, db=SimpleNamespace())

    assert response.data.refresh_token == "refresh"
    service.refresh.assert_awaited_once_with("refresh")


@pytest.mark.asyncio
@patch("app.routers.auth.AuthService")
async def test_refresh_failure(mock_service):
    service = mock_service.return_value
    service.refresh = AsyncMock(return_value=None)

    body = RefreshRequest(refresh_token="bad")
    with pytest.raises(HTTPException) as excinfo:
        await auth.refresh_token(body, db=SimpleNamespace())

    assert excinfo.value.status_code == 401


@pytest.mark.asyncio
@patch("app.routers.auth.AuthService")
async def test_logout_calls_service(mock_service):
    service = mock_service.return_value
    service.logout = AsyncMock(return_value=None)

    body = LogoutRequest(refresh_token="refresh")
    response = await auth.logout(body, current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Logout realizado com sucesso"
    service.logout.assert_awaited_once_with("refresh")


@pytest.mark.asyncio
async def test_me_returns_user():
    user = SimpleNamespace(
        id=str(uuid.uuid4()),
        name="User",
        email="user@example.com",
        role="admin",
        is_active=True,
        created_at="2024-01-01T00:00:00",
    )

    response = await auth.me(current_user=user)

    assert response.message == "Dados do usuário"
    assert response.data.email == "user@example.com"
