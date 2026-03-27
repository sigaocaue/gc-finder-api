"""Testes de integração do CRUD de reuniões do GC."""

import uuid
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


@pytest.fixture()
async def gc_id(client, editor_user, editor_token) -> str:
    """Cria um GC e retorna seu ID."""
    resp = await client.post("/api/v1/gcs/", headers=_auth_header(editor_token), json={
        "name": "GC Meetings Test",
        "zip_code": "01001000",
        "street": "Rua Teste",
        "neighborhood": "Centro",
        "city": "São Paulo",
        "state": "SP",
    })
    return resp.json()["data"]["id"]


class TestListMeetings:
    """GET /api/v1/gcs/{gc_id}/meetings/ — rota pública"""

    async def test_list_meetings_empty(self, client, gc_id):
        resp = await client.get(f"/api/v1/gcs/{gc_id}/meetings/")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_list_meetings_for_nonexistent_gc(self, client):
        resp = await client.get(f"/api/v1/gcs/{uuid.uuid4()}/meetings/")
        assert resp.status_code == 404


class TestCreateMeeting:
    """POST /api/v1/gcs/{gc_id}/meetings/ — autenticado"""

    async def test_create_meeting(self, client, gc_id, editor_token):
        resp = await client.post(
            f"/api/v1/gcs/{gc_id}/meetings/",
            headers=_auth_header(editor_token),
            json={"weekday": 3, "start_time": "19:30", "notes": "Encontro semanal"},
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["weekday"] == 3
        assert data["start_time"] == "19:30"
        assert data["notes"] == "Encontro semanal"
        assert data["gc_id"] == gc_id

    async def test_create_multiple_meetings(self, client, gc_id, editor_token):
        for day in [1, 4]:
            await client.post(
                f"/api/v1/gcs/{gc_id}/meetings/",
                headers=_auth_header(editor_token),
                json={"weekday": day, "start_time": "20:00"},
            )

        resp = await client.get(f"/api/v1/gcs/{gc_id}/meetings/")
        assert len(resp.json()["data"]) == 2


class TestUpdateMeeting:
    """PUT /api/v1/gcs/{gc_id}/meetings/{meeting_id} — autenticado"""

    async def test_update_meeting(self, client, gc_id, editor_token):
        create_resp = await client.post(
            f"/api/v1/gcs/{gc_id}/meetings/",
            headers=_auth_header(editor_token),
            json={"weekday": 2, "start_time": "18:00"},
        )
        meeting_id = create_resp.json()["data"]["id"]

        resp = await client.put(
            f"/api/v1/gcs/{gc_id}/meetings/{meeting_id}",
            headers=_auth_header(editor_token),
            json={"weekday": 5, "start_time": "19:00", "notes": "Mudou para sexta"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["weekday"] == 5
        assert data["start_time"] == "19:00"
        assert data["notes"] == "Mudou para sexta"


class TestDeleteMeeting:
    """DELETE /api/v1/gcs/{gc_id}/meetings/{meeting_id} — autenticado"""

    async def test_delete_meeting(self, client, gc_id, editor_token):
        create_resp = await client.post(
            f"/api/v1/gcs/{gc_id}/meetings/",
            headers=_auth_header(editor_token),
            json={"weekday": 0, "start_time": "10:00"},
        )
        meeting_id = create_resp.json()["data"]["id"]

        resp = await client.delete(
            f"/api/v1/gcs/{gc_id}/meetings/{meeting_id}",
            headers=_auth_header(editor_token),
        )
        assert resp.status_code == 200

        # Verifica que a reunião foi removida
        resp = await client.get(f"/api/v1/gcs/{gc_id}/meetings/")
        assert len(resp.json()["data"]) == 0

    async def test_delete_nonexistent_meeting(self, client, gc_id, editor_token):
        resp = await client.delete(
            f"/api/v1/gcs/{gc_id}/meetings/{uuid.uuid4()}",
            headers=_auth_header(editor_token),
        )
        assert resp.status_code == 404
