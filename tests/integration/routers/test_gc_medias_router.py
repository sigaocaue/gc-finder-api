"""Testes das rotas de mídias do GC."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from faker import Faker

from app.models.gc_media import GcMedia

fake = Faker()


def _medias_url(gc_id, media_id=None):
    base = f"/api/v1/gcs/{gc_id}/medias"
    return f"{base}/{media_id}" if media_id else f"{base}/"


def _make_fake_media(gc_id=None, **overrides):
    """Cria mock de GcMedia compatível com GcMediaResponse.model_validate()."""
    media = MagicMock(spec=GcMedia)
    media.id = overrides.get("id", uuid.uuid4())
    media.gc_id = gc_id or uuid.uuid4()
    media.type = overrides.get("type", fake.random_element(["image", "instagram_post", "video"]))
    media.url = overrides.get("url", fake.url())
    media.caption = overrides.get("caption", fake.sentence())
    media.display_order = overrides.get("display_order", 0)
    media.created_at = overrides.get("created_at", datetime.now())
    return media


class TestListMedias:
    """Testa GET /api/v1/gcs/{gc_id}/medias/ (pública)."""

    @patch("app.routers.gc_medias.GcService")
    def test_list_medias_success(self, MockService, client):
        """Deve retornar 200 com lista de mídias."""
        gc_id = uuid.uuid4()
        mock_service = MockService.return_value
        mock_service.list_medias = AsyncMock(return_value=[
            _make_fake_media(gc_id), _make_fake_media(gc_id),
        ])
        resp = client.get(_medias_url(gc_id))
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2


class TestCreateMedia:
    """Testa POST /api/v1/gcs/{gc_id}/medias/ (autenticada)."""

    @patch("app.routers.gc_medias.GcService")
    def test_create_media_success(self, MockService, client):
        """Payload válido deve retornar 201."""
        gc_id = uuid.uuid4()
        media = _make_fake_media(gc_id)
        mock_service = MockService.return_value
        mock_service.create_media = AsyncMock(return_value=media)
        resp = client.post(_medias_url(gc_id), json={
            "type": "image",
            "url": fake.url(),
            "caption": fake.sentence(),
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["id"] == str(media.id)


class TestUpdateMedia:
    """Testa PUT /api/v1/gcs/{gc_id}/medias/{media_id} (autenticada)."""

    @patch("app.routers.gc_medias.GcService")
    def test_update_media_success(self, MockService, client):
        """Atualização deve retornar 200."""
        gc_id = uuid.uuid4()
        media = _make_fake_media(gc_id)
        mock_service = MockService.return_value
        mock_service.update_media = AsyncMock(return_value=media)
        resp = client.put(_medias_url(gc_id, media.id), json={
            "caption": fake.sentence(),
        })
        assert resp.status_code == 200


class TestDeleteMedia:
    """Testa DELETE /api/v1/gcs/{gc_id}/medias/{media_id} (autenticada)."""

    @patch("app.routers.gc_medias.GcService")
    def test_delete_media_success(self, MockService, client):
        """Remoção deve retornar 200."""
        gc_id = uuid.uuid4()
        media_id = uuid.uuid4()
        mock_service = MockService.return_value
        mock_service.delete_media = AsyncMock()
        resp = client.delete(_medias_url(gc_id, media_id))
        assert resp.status_code == 200
        assert resp.json()["message"]
