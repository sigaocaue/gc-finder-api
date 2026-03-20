"""Unit tests for the user service."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services import user_service
from app.services.user_service import UserService


@pytest.fixture
def db_session():
    session = MagicMock(spec=AsyncMock)
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(monkeypatch):
    repo_mock = AsyncMock()
    repo_mock.get_all = AsyncMock()
    repo_mock.get_by_id = AsyncMock()
    repo_mock.get_by_email = AsyncMock()
    repo_mock.create = AsyncMock()
    repo_mock.update = AsyncMock()
    repo_mock.deactivate = AsyncMock()
    monkeypatch.setattr(
        user_service, "UserRepository", lambda db: repo_mock
    )
    return repo_mock


@pytest.fixture
def service(db_session, repo):
    return UserService(db_session)


@pytest.fixture
def hashed(monkeypatch):
    counter = {"calls": 0}

    def fake_hash(password: str) -> str:
        counter["calls"] += 1
        return f"hashed-{password}"

    monkeypatch.setattr(user_service, "hash_password", fake_hash)
    return counter


@pytest.mark.asyncio
async def test_list_all(service, repo):
    repo.get_all.return_value = [User(name="A"), User(name="B")]
    result = await service.list_all()

    assert result == repo.get_all.return_value
    repo.get_all.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_id_success(service, repo):
    leader = User(name="Test")
    repo.get_by_id.return_value = leader

    assert await service.get_by_id("uid") is leader
    repo.get_by_id.assert_awaited_once_with("uid")


@pytest.mark.asyncio
async def test_get_by_id_raises_not_found(service, repo):
    repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as excinfo:
        await service.get_by_id("missing")

    assert excinfo.value.status_code == 404
    assert "Usuário não encontrado" in excinfo.value.detail


@pytest.mark.asyncio
async def test_create_user_hashes_password(service, repo, hashed):
    repo.get_by_email.return_value = None
    user = User(name="Novo", email="novo@example.com")
    repo.create.return_value = user
    data = UserCreate(name="Novo", email="novo@example.com", password="secret", role="admin")

    result = await service.create(data)

    assert result is user
    repo.get_by_email.assert_awaited_once_with("novo@example.com")
    repo.create.assert_awaited_once()
    assert repo.create.call_args[0][0].password_hash == "hashed-secret"
    assert hashed["calls"] == 1


@pytest.mark.asyncio
async def test_create_user_conflict(service, repo):
    repo.get_by_email.return_value = User(name="Exist")
    data = UserCreate(name="Novo", email="exist@example.com", password="secret", role="admin")

    with pytest.raises(HTTPException) as excinfo:
        await service.create(data)

    assert excinfo.value.status_code == 409


@pytest.mark.asyncio
async def test_update_changes_fields_and_hashes_password(service, repo, hashed):
    user = User(name="Original", email="old@example.com", password_hash="old", role="editor")
    service.get_by_id = AsyncMock(return_value=user)
    repo.update.return_value = user
    repo.get_by_email.return_value = None
    data = UserUpdate(name="New", email="new@example.com", password="newpass", role="admin")

    result = await service.update("uid", data)

    assert result is user
    assert user.name == "New"
    assert user.email == "new@example.com"
    assert user.role == "admin"
    assert user.password_hash == "hashed-newpass"
    repo.get_by_email.assert_awaited_once_with("new@example.com")
    repo.update.assert_awaited_once_with(user)
    assert hashed["calls"] == 1


@pytest.mark.asyncio
async def test_update_shared_email_does_not_hash(service, repo, hashed):
    hashed["calls"] = 0
    user = User(name="Original", email="same@example.com", password_hash="old")
    service.get_by_id = AsyncMock(return_value=user)
    repo.update.return_value = user
    data = UserUpdate(name="Other")

    result = await service.update("uid", data)

    assert result is user
    assert hashed["calls"] == 0
    repo.update.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_update_email_conflict(service, repo):
    user = User(name="Original", email="old@example.com")
    service.get_by_id = AsyncMock(return_value=user)
    repo.get_by_email.return_value = User(name="Other")
    data = UserUpdate(email="other@example.com")

    with pytest.raises(HTTPException) as excinfo:
        await service.update("uid", data)

    assert excinfo.value.status_code == 409


@pytest.mark.asyncio
async def test_deactivate_user(service, repo):
    user = User(name="ToDeactivate")
    service.get_by_id = AsyncMock(return_value=user)
    repo.deactivate.return_value = user

    result = await service.deactivate("uid")

    assert result is user
    repo.deactivate.assert_awaited_once_with(user)
