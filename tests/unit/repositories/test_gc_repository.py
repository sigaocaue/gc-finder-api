"""Unit tests for the GC repository behaviors."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.repositories.gc_repository import GcRepository


class DummyScalar:
    def __init__(self, items):
        self._items = items

    def first(self):
        return self._items[0] if self._items else None

    def all(self):
        return self._items


@pytest.fixture
def session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def repo(session):
    return GcRepository(session)


def _set_result(session, rows):
    result = MagicMock()
    result.scalars.return_value = DummyScalar(rows)
    session.execute.return_value = result


@pytest.fixture(autouse=True)
def allow_extra_gcleader_args(monkeypatch):
    from app.models.gc_leader import GcLeader

    orig_init = GcLeader.__init__

    def patched_init(self, *args, **kwargs):
        kwargs.pop("is_primary", None)
        return orig_init(self, *args, **kwargs)

    monkeypatch.setattr(GcLeader, "__init__", patched_init)
    yield


@pytest.mark.asyncio
async def test_get_by_id(session, repo):
    candidate = MagicMock()
    _set_result(session, [candidate])

    assert await repo.get_by_id("gc-id") is candidate
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_active(session, repo):
    rows = [MagicMock(), MagicMock()]
    _set_result(session, rows)

    assert await repo.get_all_active() == rows
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_all_active_with_coords(session, repo):
    rows = [MagicMock()]
    _set_result(session, rows)

    assert await repo.get_all_active_with_coords() == rows
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_create(session, repo):
    model = MagicMock()

    result = await repo.create(model)

    assert result is model
    session.add.assert_called_once_with(model)
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(model)


@pytest.mark.asyncio
async def test_update(session, repo):
    model = MagicMock()

    result = await repo.update(model)

    assert result is model
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(model)


@pytest.mark.asyncio
async def test_deactivate(session, repo):
    model = MagicMock()

    result = await repo.deactivate(model)

    assert result is model
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(model)
    assert model.is_active is False


@pytest.mark.asyncio
async def test_add_leader(session, repo):
    await repo.add_leader("gc-id", "leader-id", is_primary=True)

    added = session.add.call_args[0][0]
    assert added.gc_id == "gc-id"
    assert added.leader_id == "leader-id"
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_leader(session, repo):
    await repo.remove_leader("gc-id", "leader-id")

    session.execute.assert_awaited_once()
    assert "gc_leaders" in str(session.execute.call_args[0][0])
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_meetings(session, repo):
    records = [MagicMock(), MagicMock()]
    _set_result(session, records)

    assert await repo.get_meetings("gc-id") == records
    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_meeting_by_id(session, repo):
    meeting = MagicMock()
    _set_result(session, [meeting])

    assert await repo.get_meeting_by_id("meet-id") is meeting


@pytest.mark.asyncio
async def test_create_meeting(session, repo):
    meeting = MagicMock()
    result = await repo.create_meeting(meeting)

    assert result is meeting
    session.add.assert_called_once_with(meeting)
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(meeting)


@pytest.mark.asyncio
async def test_update_meeting(session, repo):
    meeting = MagicMock()
    result = await repo.update_meeting(meeting)

    assert result is meeting
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(meeting)


@pytest.mark.asyncio
async def test_delete_meeting(session, repo):
    meeting = MagicMock()
    await repo.delete_meeting(meeting)

    session.delete.assert_awaited_once_with(meeting)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_medias(session, repo):
    medias = [MagicMock(), MagicMock()]
    _set_result(session, medias)

    assert await repo.get_medias("gc-id") == medias


@pytest.mark.asyncio
async def test_get_media_by_id(session, repo):
    media = MagicMock()
    _set_result(session, [media])

    assert await repo.get_media_by_id("media-id") is media


@pytest.mark.asyncio
async def test_create_media(session, repo):
    media = MagicMock()
    result = await repo.create_media(media)

    assert result is media
    session.add.assert_called_once_with(media)
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(media)


@pytest.mark.asyncio
async def test_update_media(session, repo):
    media = MagicMock()
    result = await repo.update_media(media)

    assert result is media
    session.flush.assert_awaited_once()
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(media)


@pytest.mark.asyncio
async def test_delete_media(session, repo):
    media = MagicMock()
    await repo.delete_media(media)

    session.delete.assert_awaited_once_with(media)
    session.commit.assert_awaited_once()
