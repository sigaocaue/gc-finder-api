"""Testes de integração do CRUD de GCs e vínculo com líderes."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from tests.integration.conftest import _auth_header


# Coordenadas fake para testes (evita chamada real ao Google Maps)
_FAKE_COORDS = (-23.5505199, -46.6333094)


@pytest.fixture(autouse=True)
def _mock_geocoding():
    """Mocka o serviço de geocodificação para evitar chamadas externas."""
    with patch(
        "app.services.gc_service.fetch_coordinates",
        new_callable=AsyncMock,
        return_value=_FAKE_COORDS,
    ):
        yield


def _gc_payload(**overrides) -> dict:
    defaults = {
        "name": "GC Integração",
        "zip_code": "01001000",
        "street": "Praça da Sé",
        "neighborhood": "Sé",
        "city": "São Paulo",
        "state": "SP",
        "leaders": [],
        "meetings": [],
        "medias": [],
    }
    defaults.update(overrides)
    return defaults


class TestListGcs:
    """GET /api/v1/gcs/ — rota pública"""

    async def test_list_gcs_empty(self, client):
        resp = await client.get("/api/v1/gcs/")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_list_gcs_with_pagination(self, client, editor_user, editor_token):
        # Cria 3 GCs
        for i in range(3):
            await client.post(
                "/api/v1/gcs/",
                headers=_auth_header(editor_token),
                json=_gc_payload(name=f"GC {i}"),
            )

        # Pega os 2 primeiros
        resp = await client.get("/api/v1/gcs/?skip=0&limit=2")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2


class TestCreateGc:
    """POST /api/v1/gcs/ — autenticado"""

    async def test_create_gc_basic(self, client, editor_user, editor_token):
        resp = await client.post(
            "/api/v1/gcs/",
            headers=_auth_header(editor_token),
            json=_gc_payload(),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "GC Integração"
        assert data["city"] == "São Paulo"
        assert data["is_active"] is True
        assert data["latitude"] is not None
        assert data["longitude"] is not None

    async def test_create_gc_with_meetings_and_medias(self, client, editor_user, editor_token):
        resp = await client.post(
            "/api/v1/gcs/",
            headers=_auth_header(editor_token),
            json=_gc_payload(
                meetings=[{"weekday": 3, "start_time": "19:30", "notes": "Quarta-feira"}],
                medias=[{"type": "image", "url": "https://example.com/photo.jpg", "display_order": 0}],
            ),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert len(data["meetings"]) == 1
        assert data["meetings"][0]["weekday"] == 3
        assert data["meetings"][0]["start_time"] == "19:30"
        assert len(data["medias"]) == 1

    async def test_create_gc_with_leader(self, client, create_leader, editor_user, editor_token):
        leader = await create_leader(name="Líder do GC")
        resp = await client.post(
            "/api/v1/gcs/",
            headers=_auth_header(editor_token),
            json=_gc_payload(leaders=[str(leader.id)]),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert len(data["leaders"]) == 1
        assert data["leaders"][0]["name"] == "Líder do GC"

    async def test_create_gc_without_auth_returns_401(self, client):
        resp = await client.post("/api/v1/gcs/", json=_gc_payload())
        assert resp.status_code in (401, 403)


class TestGetGc:
    """GET /api/v1/gcs/{gc_id} — rota pública"""

    async def test_get_gc_with_relations(self, client, create_leader, editor_user, editor_token):
        leader = await create_leader()
        create_resp = await client.post(
            "/api/v1/gcs/",
            headers=_auth_header(editor_token),
            json=_gc_payload(
                leaders=[str(leader.id)],
                meetings=[{"weekday": 1, "start_time": "20:00"}],
            ),
        )
        gc_id = create_resp.json()["data"]["id"]

        resp = await client.get(f"/api/v1/gcs/{gc_id}")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data["leaders"]) == 1
        assert len(data["meetings"]) == 1

    async def test_get_gc_not_found(self, client):
        resp = await client.get(f"/api/v1/gcs/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestUpdateGc:
    """PUT /api/v1/gcs/{gc_id} — autenticado"""

    async def test_update_gc_name(self, client, editor_user, editor_token):
        create_resp = await client.post(
            "/api/v1/gcs/",
            headers=_auth_header(editor_token),
            json=_gc_payload(),
        )
        gc_id = create_resp.json()["data"]["id"]

        resp = await client.put(
            f"/api/v1/gcs/{gc_id}",
            headers=_auth_header(editor_token),
            json={"name": "GC Atualizado"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "GC Atualizado"

    async def test_update_gc_partial_address_fails(self, client, editor_user, editor_token):
        """Enviar apenas zip_code sem os outros campos de endereço deve falhar."""
        create_resp = await client.post(
            "/api/v1/gcs/",
            headers=_auth_header(editor_token),
            json=_gc_payload(),
        )
        gc_id = create_resp.json()["data"]["id"]

        resp = await client.put(
            f"/api/v1/gcs/{gc_id}",
            headers=_auth_header(editor_token),
            json={"zip_code": "02002000"},
        )
        assert resp.status_code == 422


class TestDeactivateGc:
    """DELETE /api/v1/gcs/{gc_id} — autenticado"""

    async def test_deactivate_gc(self, client, editor_user, editor_token):
        create_resp = await client.post(
            "/api/v1/gcs/",
            headers=_auth_header(editor_token),
            json=_gc_payload(),
        )
        gc_id = create_resp.json()["data"]["id"]

        resp = await client.delete(
            f"/api/v1/gcs/{gc_id}",
            headers=_auth_header(editor_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_active"] is False


class TestGcLeaderLink:
    """POST/DELETE /api/v1/gcs/{gc_id}/leaders — autenticado"""

    async def test_link_and_unlink_leader(self, client, create_leader, editor_user, editor_token):
        # Cria GC sem líder
        create_resp = await client.post(
            "/api/v1/gcs/",
            headers=_auth_header(editor_token),
            json=_gc_payload(),
        )
        gc_id = create_resp.json()["data"]["id"]
        leader = await create_leader(name="Novo Líder")

        # Vincula líder
        resp = await client.post(
            f"/api/v1/gcs/{gc_id}/leaders",
            headers=_auth_header(editor_token),
            json={"leader_id": str(leader.id)},
        )
        assert resp.status_code == 201
        assert len(resp.json()["data"]["leaders"]) == 1

        # Desvincula líder
        resp = await client.delete(
            f"/api/v1/gcs/{gc_id}/leaders/{leader.id}",
            headers=_auth_header(editor_token),
        )
        assert resp.status_code == 200

    async def test_link_duplicate_leader_returns_409(self, client, create_leader, editor_user, editor_token):
        leader = await create_leader()
        create_resp = await client.post(
            "/api/v1/gcs/",
            headers=_auth_header(editor_token),
            json=_gc_payload(leaders=[str(leader.id)]),
        )
        gc_id = create_resp.json()["data"]["id"]

        # Tenta vincular o mesmo líder novamente
        resp = await client.post(
            f"/api/v1/gcs/{gc_id}/leaders",
            headers=_auth_header(editor_token),
            json={"leader_id": str(leader.id)},
        )
        assert resp.status_code == 409
