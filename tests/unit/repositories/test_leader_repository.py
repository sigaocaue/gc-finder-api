"""Unit tests for the leader repository helper."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.leader import Leader
from app.repositories.leader_repository import LeaderRepository


class DummyScalar:
    def __init__(self, items):
        self._items = items

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return self._items


@pytest.fixture
def session():
    sess = AsyncMock()
    sess.execute = AsyncMock()
    sess.flush = AsyncMock()
    sess.commit = AsyncMock()
    sess.refresh = AsyncMock()
    sess.add = MagicMock()
    return sess


@pytest.fixture
def repo(session):
    return LeaderRepository(session)


def _set_scalar_result(session, rows):
    result = MagicMock()
    result.scalars.return_value = DummyScalar(rows)
    session.execute.return_value = result


@pytest.mark.asyncio
async def test_get_by_id(session, repo):
    leader = MagicMock()
    _set_scalar_result(session, [leader])

    assert await repo.get_by_id("leader-id") is leader
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_active(session, repo):
    leaders = [MagicMock(), MagicMock()]
    _set_scalar_result(session, leaders)

    assert await repo.get_all_active() == leaders
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_leader(session, repo):
    leader = Leader(name="Test")
    result = await repo.create(leader)

    assert result is leader
    session.add.assert_called_once_with(leader)
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(leader)


@pytest.mark.asyncio
async def test_update_leader(session, repo):
    leader = MagicMock()
    result = await repo.update(leader)

    assert result is leader
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(leader)


@pytest.mark.asyncio
async def test_deactivate_leader(session, repo):
    leader = MagicMock()
    result = await repo.deactivate(leader)

    assert result is leader
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(leader)
    assert leader.is_active is False
