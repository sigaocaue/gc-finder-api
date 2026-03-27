"""Testes de integração do health check com banco real."""

import pytest


class TestHealthCheck:
    """GET /health"""

    async def test_health_with_db(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "healthy"
        assert data["database"] == "connected"
