"""Testes da rota GET /health."""

from unittest.mock import AsyncMock


class TestHealthCheck:
    """Testa o endpoint de health check."""

    def test_health_success(self, client, mock_db):
        """Banco respondendo deve retornar healthy."""
        mock_db.execute = AsyncMock()
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "healthy"
        assert body["data"]["database"] == "connected"

    def test_health_db_error(self, client, mock_db):
        """Falha no banco deve retornar unhealthy (sem erro HTTP)."""
        mock_db.execute = AsyncMock(side_effect=Exception("connection refused"))
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["status"] == "unhealthy"
        assert body["data"]["database"] == "disconnected"
