"""Unit tests for the users router."""

from datetime import datetime
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.routers import users


class FakeUser(SimpleNamespace):
    pass


def build_user(*, name, email, role="editor", is_active=True):
    return FakeUser(
        id=str(uuid.uuid4()),
        name=name,
        email=email,
        role=role,
        is_active=is_active,
        created_at=datetime.now(),
    )


@pytest.fixture
def admin():
    return SimpleNamespace(id="admin-1", email="admin@example.com")


@pytest.fixture
def db():
    return SimpleNamespace()


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [1, 2])
@patch("app.routers.users.UserService")
async def test_list_users(mock_service, admin, db, count):
    service = mock_service.return_value
    users_list = [
        build_user(name=f"User {idx}", email=f"user{idx}@example.com")
        for idx in range(count)
    ]
    first_user = users_list[0]
    service.list_all = AsyncMock(return_value=users_list)

    response = await users.list_users(admin, db)

    assert response.message == "Lista de usuários"
    assert len(response.data) == count
    assert response.data[0].email == first_user.email
    service.list_all.assert_awaited_once()
    mock_service.assert_called_once_with(db)


@pytest.mark.asyncio
@patch("app.routers.users.UserService")
async def test_get_user_found(mock_service, admin, db):
    service = mock_service.return_value
    user = build_user(
        name="User Two",
        email="two@example.com",
        role="admin",
    )
    service.get_by_id = AsyncMock(return_value=user)

    response = await users.get_user("u2", admin, db)

    assert response.message == "Usuário encontrado"
    assert str(response.data.id) == user.id
    service.get_by_id.assert_awaited_once_with("u2")


@pytest.mark.asyncio
@patch("app.routers.users.UserService")
async def test_get_user_not_found(mock_service, admin, db):
    service = mock_service.return_value
    service.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as excinfo:
        await users.get_user("missing", admin, db)

    assert excinfo.value.status_code == 404
    assert "Usuário não encontrado" in excinfo.value.detail


@pytest.mark.asyncio
@patch("app.routers.users.UserService")
async def test_create_user(mock_service, admin, db):
    service = mock_service.return_value
    user = build_user(
        name="User Three",
        email="three@example.com",
        role="editor",
    )
    service.create = AsyncMock(return_value=user)
    body = SimpleNamespace(name="User Three", email="three@example.com", password="secret", role="editor")

    response = await users.create_user(body, admin, db)

    assert response.message == "Usuário criado com sucesso"
    assert response.data.email == "three@example.com"
    service.create.assert_awaited_once_with(body)


@pytest.mark.asyncio
@patch("app.routers.users.UserService")
async def test_update_user_success(mock_service, admin, db):
    service = mock_service.return_value
    user = build_user(
        name="User Four",
        email="four@example.com",
        role="editor",
    )
    service.update = AsyncMock(return_value=user)
    body = SimpleNamespace(name="User Four Updated")

    response = await users.update_user("u4", body, admin, db)

    assert response.message == "Usuário atualizado com sucesso"
    assert response.data.name == "User Four"
    service.update.assert_awaited_once_with("u4", body)


@pytest.mark.asyncio
@patch("app.routers.users.UserService")
async def test_update_user_not_found(mock_service, admin, db):
    service = mock_service.return_value
    service.update = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as excinfo:
        await users.update_user("u4", SimpleNamespace(), admin, db)

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
@patch("app.routers.users.UserService")
async def test_deactivate_user_success(mock_service, admin, db):
    service = mock_service.return_value
    user = build_user(
        name="User Five",
        email="five@example.com",
        role="editor",
        is_active=False,
    )
    service.deactivate = AsyncMock(return_value=user)

    response = await users.deactivate_user("u5", admin, db)

    assert response.message == "Usuário desativado com sucesso"
    assert response.data.is_active is False
    service.deactivate.assert_awaited_once_with("u5")


@pytest.mark.asyncio
@patch("app.routers.users.UserService")
async def test_deactivate_user_not_found(mock_service, admin, db):
    service = mock_service.return_value
    service.deactivate = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as excinfo:
        await users.deactivate_user("missing", admin, db)

    assert excinfo.value.status_code == 404
