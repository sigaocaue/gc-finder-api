"""Unit tests for the user repository."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.user import User
from app.repositories.user_repository import UserRepository


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
    return UserRepository(session)


def _set_scalar_result(session, rows):
    result = MagicMock()
    result.scalars.return_value = DummyScalar(rows)
    session.execute.return_value = result


@pytest.mark.asyncio
async def test_get_by_id(session, repo):
    user = MagicMock()
    _set_scalar_result(session, [user])

    assert await repo.get_by_id("user-id") is user
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_email(session, repo):
    user = MagicMock()
    _set_scalar_result(session, [user])

    assert await repo.get_by_email("mail@example.com") is user
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all(session, repo):
    users = [MagicMock(), MagicMock()]
    _set_scalar_result(session, users)

    assert await repo.get_all() == users
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create(session, repo):
    user = User(name="New", email="new@example.com", role="viewer")
    result = await repo.create(user)

    assert result is user
    session.add.assert_called_once_with(user)
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_update(session, repo):
    user = MagicMock()
    result = await repo.update(user)

    assert result is user
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_deactivate(session, repo):
    user = MagicMock()
    result = await repo.deactivate(user)

    assert result is user
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(user)
    assert user.is_active is False
