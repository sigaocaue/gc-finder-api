"""Testes de integração do CRUD de mídias do GC."""

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
        "name": "GC Medias Test",
        "zip_code": "01001000",
        "street": "Rua Teste",
        "neighborhood": "Centro",
        "city": "São Paulo",
        "state": "SP",
    })
    return resp.json()["data"]["id"]


class TestListMedias:
    """GET /api/v1/gcs/{gc_id}/medias/ — rota pública"""

    async def test_list_medias_empty(self, client, gc_id):
        resp = await client.get(f"/api/v1/gcs/{gc_id}/medias/")
        assert resp.status_code == 200
        assert resp.json()["data"] == []


class TestCreateMedia:
    """POST /api/v1/gcs/{gc_id}/medias/ — autenticado"""

    async def test_create_image_media(self, client, gc_id, editor_token):
        resp = await client.post(
            f"/api/v1/gcs/{gc_id}/medias/",
            headers=_auth_header(editor_token),
            json={
                "type": "image",
                "url": "https://example.com/photo.jpg",
                "caption": "Foto do encontro",
                "display_order": 1,
            },
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["type"] == "image"
        assert data["url"] == "https://example.com/photo.jpg"
        assert data["caption"] == "Foto do encontro"
        assert data["display_order"] == 1

    async def test_create_video_media(self, client, gc_id, editor_token):
        resp = await client.post(
            f"/api/v1/gcs/{gc_id}/medias/",
            headers=_auth_header(editor_token),
            json={"type": "video", "url": "https://youtube.com/watch?v=abc"},
        )
        assert resp.status_code == 201
        assert resp.json()["data"]["type"] == "video"

    async def test_create_media_invalid_type(self, client, gc_id, editor_token):
        resp = await client.post(
            f"/api/v1/gcs/{gc_id}/medias/",
            headers=_auth_header(editor_token),
            json={"type": "podcast", "url": "https://example.com/audio.mp3"},
        )
        assert resp.status_code == 422


class TestUpdateMedia:
    """PUT /api/v1/gcs/{gc_id}/medias/{media_id} — autenticado"""

    async def test_update_media_caption(self, client, gc_id, editor_token):
        create_resp = await client.post(
            f"/api/v1/gcs/{gc_id}/medias/",
            headers=_auth_header(editor_token),
            json={"type": "image", "url": "https://example.com/1.jpg"},
        )
        media_id = create_resp.json()["data"]["id"]

        resp = await client.put(
            f"/api/v1/gcs/{gc_id}/medias/{media_id}",
            headers=_auth_header(editor_token),
            json={"caption": "Nova legenda", "display_order": 5},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["caption"] == "Nova legenda"
        assert data["display_order"] == 5


class TestDeleteMedia:
    """DELETE /api/v1/gcs/{gc_id}/medias/{media_id} — autenticado"""

    async def test_delete_media(self, client, gc_id, editor_token):
        create_resp = await client.post(
            f"/api/v1/gcs/{gc_id}/medias/",
            headers=_auth_header(editor_token),
            json={"type": "image", "url": "https://example.com/delete.jpg"},
        )
        media_id = create_resp.json()["data"]["id"]

        resp = await client.delete(
            f"/api/v1/gcs/{gc_id}/medias/{media_id}",
            headers=_auth_header(editor_token),
        )
        assert resp.status_code == 200

        # Verifica que a mídia foi removida
        resp = await client.get(f"/api/v1/gcs/{gc_id}/medias/")
        assert len(resp.json()["data"]) == 0

    async def test_delete_nonexistent_media(self, client, gc_id, editor_token):
        resp = await client.delete(
            f"/api/v1/gcs/{gc_id}/medias/{uuid.uuid4()}",
            headers=_auth_header(editor_token),
        )
        assert resp.status_code == 404
