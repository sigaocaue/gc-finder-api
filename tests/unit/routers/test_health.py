"""Unit tests for the health check router."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.routers.health import health_check


@pytest.mark.asyncio
async def test_health_check_success(monkeypatch):
    db = SimpleNamespace()
    db.execute = AsyncMock(return_value=None)

    response = await health_check(db)

    assert response.message == "API operacional"
    assert response.data == {"status": "healthy", "database": "connected"}
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_health_check_failure_logs(monkeypatch):
    db = SimpleNamespace()
    db.execute = AsyncMock(side_effect=RuntimeError("boom"))
    logged = []

    class FakeLogger:
        def error(self, msg, *args):
            logged.append(msg % args)

    monkeypatch.setattr("app.routers.health.logger", FakeLogger())

    response = await health_check(db)

    assert response.message == "Falha na conexão com o banco de dados"
    assert response.data == {"status": "unhealthy", "database": "disconnected"}
    assert "bo" in logged[0]
