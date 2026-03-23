"""Unit tests for the leader service logic."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.leader import Leader
from app.models.leader_contact import LeaderContact
from app.schemas.leader import LeaderContactCreate, LeaderCreate, LeaderUpdate
from app.services import leader_service
from app.services.leader_service import LeaderService


@pytest.fixture
def db_session():
    session = MagicMock(spec=AsyncSession)
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(monkeypatch):
    repo_mock = AsyncMock()
    repo_mock.get_all_active = AsyncMock()
    repo_mock.get_by_id = AsyncMock()
    repo_mock.create = AsyncMock()
    repo_mock.update = AsyncMock()
    repo_mock.deactivate = AsyncMock()
    monkeypatch.setattr(
        leader_service, "LeaderRepository", lambda db: repo_mock
    )
    return repo_mock


@pytest.fixture
def service(db_session, repo):
    return LeaderService(db_session)


@pytest.mark.asyncio
async def test_list_all_delegates_to_repository(service, repo):
    leader_list = [Leader(name="Ana"), Leader(name="Rafael")]
    repo.get_all_active.return_value = leader_list

    assert await service.list_all() == leader_list
    repo.get_all_active.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_id_returns_leader(service, repo):
    leader = Leader(name="Fernanda")
    repo.get_by_id.return_value = leader

    assert await service.get_by_id("leader-id") is leader
    repo.get_by_id.assert_awaited_once_with("leader-id")


@pytest.mark.asyncio
async def test_get_by_id_raises_when_missing(service, repo):
    repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as excinfo:
        await service.get_by_id("missing")

    assert excinfo.value.status_code == 404
    assert "Líder não encontrado" in excinfo.value.detail


@pytest.mark.asyncio
async def test_create_persists_contacts_and_leader(service, repo, db_session):
    create_data = LeaderCreate(
        name="Leonardo",
        bio="Bio",
        contacts=[
            LeaderContactCreate(type="email", value="leo@example.com"),
            LeaderContactCreate(type="phone", value="+55 11 99999"),
        ],
    )
    leader = Leader(name="Leonardo")
    repo.create.return_value = leader

    result = await service.create(create_data)

    assert result is leader
    assert db_session.add.call_count == 2
    for call in db_session.add.call_args_list:
        added = call.args[0]
        assert isinstance(added, LeaderContact)
        assert isinstance(added.leader, Leader)
        assert added.leader.name == leader.name
    repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_applies_fields_before_repo_call(service, repo):
    original = Leader(name="Original")
    service.get_by_id = AsyncMock(return_value=original)
    repo.update.return_value = original
    update = LeaderUpdate(name="Updated", bio="New bio", is_active=False)

    result = await service.update("id", update)

    assert result is original
    assert original.name == "Updated"
    assert original.bio == "New bio"
    assert original.is_active is False
    repo.update.assert_awaited_once_with(original)


@pytest.mark.asyncio
async def test_deactivate_marks_leader_inactive(service, repo):
    leader = Leader(name="ToDeactivate")
    service.get_by_id = AsyncMock(return_value=leader)
    repo.deactivate.return_value = leader

    result = await service.deactivate("id")

    assert result is leader
    repo.deactivate.assert_awaited_once_with(leader)
