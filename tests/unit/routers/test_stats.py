"""Unit tests for the stats router."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.routers.stats import get_entity_counts


class DummyResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value


@pytest.mark.asyncio
async def test_get_entity_counts_returns_every_entity(monkeypatch):
    counts = [2, 3, 4, 5, 6, 7]
    db = SimpleNamespace()
    db.execute = AsyncMock(side_effect=[DummyResult(value) for value in counts])

    current_user = SimpleNamespace(email="admin@example.com")

    response = await get_entity_counts(db, current_user)

    assert response.message == "Contagem de registros por entidade"
    assert response.data.users == counts[0]
    assert response.data.leaders == counts[1]
    assert response.data.gcs == counts[2]
    assert response.data.meetings == counts[3]
    assert response.data.medias == counts[4]
    assert response.data.leader_contacts == counts[5]
    assert db.execute.call_count == 6


@pytest.mark.asyncio
async def test_get_entity_counts_uses_current_user_email(monkeypatch):
    counts = [1, 1, 1, 1, 1, 1]
    db = SimpleNamespace()
    db.execute = AsyncMock(side_effect=[DummyResult(value) for value in counts])

    logs = []

    class FakeLogger:
        def info(self, msg, *args, **kwargs):
            logs.append(msg % args)

    monkeypatch.setattr("app.routers.stats.logger", FakeLogger())

    user = SimpleNamespace(email="stats@example.com")
    await get_entity_counts(db, user)

    assert "stats@example.com" in logs[0]
