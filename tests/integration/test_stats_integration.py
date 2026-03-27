"""Testes de integração da rota de estatísticas."""

from unittest.mock import AsyncMock, patch

import pytest

from tests.integration.conftest import _auth_header


@pytest.fixture(autouse=True)
def _mock_geocoding():
    with patch(
        "app.services.gc_service.fetch_coordinates",
        new_callable=AsyncMock,
        return_value=(-23.55, -46.63),
    ):
        yield


class TestEntityCounts:
    """GET /api/v1/stats/counts — requer admin"""

    async def test_counts_empty_db(self, client, admin_user, admin_token):
        resp = await client.get("/api/v1/stats/counts", headers=_auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        # O admin_user já existe, então users=1
        assert data["users"] == 1
        assert data["leaders"] == 0
        assert data["gcs"] == 0
        assert data["meetings"] == 0
        assert data["medias"] == 0
        assert data["leader_contacts"] == 0

    async def test_counts_after_creating_entities(
        self, client, admin_user, admin_token, create_leader, editor_user
    ):
        # Cria líder com contato
        await client.post("/api/v1/leaders/", headers=_auth_header(admin_token), json={
            "name": "Count Leader",
            "contacts": [{"type": "email", "value": "leader@test.com"}],
        })

        # Cria GC com reunião e mídia
        await client.post("/api/v1/gcs/", headers=_auth_header(admin_token), json={
            "name": "Count GC",
            "zip_code": "01001000",
            "street": "Rua A",
            "neighborhood": "Centro",
            "city": "São Paulo",
            "state": "SP",
            "meetings": [{"weekday": 1, "start_time": "19:00"}],
            "medias": [{"type": "image", "url": "https://example.com/img.jpg"}],
        })

        resp = await client.get("/api/v1/stats/counts", headers=_auth_header(admin_token))
        data = resp.json()["data"]
        # admin_user + editor_user
        assert data["users"] == 2
        assert data["leaders"] == 1
        assert data["gcs"] == 1
        assert data["meetings"] == 1
        assert data["medias"] == 1
        assert data["leader_contacts"] == 1

    async def test_counts_as_editor_returns_403(self, client, editor_user, editor_token):
        resp = await client.get("/api/v1/stats/counts", headers=_auth_header(editor_token))
        assert resp.status_code == 403

    async def test_counts_without_auth_returns_401(self, client):
        resp = await client.get("/api/v1/stats/counts")
        assert resp.status_code in (401, 403)
