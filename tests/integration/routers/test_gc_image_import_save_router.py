"""Testes da rota POST /api/v1/gcs/import/save — salvamento de GC importado."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker

from app.models.gc import Gc

fake = Faker("pt_BR")

SAVE_ENDPOINT = "/api/v1/gcs/import/save"


def _build_save_payload(**overrides) -> dict:
    """Gera payload válido para o endpoint /save usando Faker."""
    base = {
        "name": fake.company(),
        "description": fake.sentence(),
        "zip_code": fake.postcode().replace("-", ""),
        "street": fake.street_name(),
        "number": fake.building_number(),
        "complement": f"Apto {fake.building_number()}",
        "neighborhood": fake.bairro(),
        "city": fake.city(),
        "state": fake.state_abbr(),
        "latitude": float(fake.latitude()),
        "longitude": float(fake.longitude()),
        "leaders": [],
        "meetings": [],
    }
    base.update(overrides)
    return base


def _build_gc_mock(payload: dict) -> MagicMock:
    """Cria um mock de Gc compatível com GcResponse.model_validate."""
    gc = MagicMock(spec=Gc)
    gc.id = uuid.uuid4()
    gc.name = payload["name"]
    gc.description = payload.get("description")
    gc.zip_code = payload.get("zip_code", "00000000")
    gc.street = payload["street"]
    gc.number = payload.get("number")
    gc.complement = payload.get("complement")
    gc.neighborhood = payload.get("neighborhood", "Centro")
    gc.city = payload.get("city", "Jundiaí")
    gc.state = payload.get("state", "SP")
    gc.latitude = payload.get("latitude")
    gc.longitude = payload.get("longitude")
    gc.is_active = True
    gc.created_at = datetime.now()
    gc.updated_at = datetime.now()
    gc.leader_associations = []
    gc.meetings = []
    gc.medias = []
    return gc


# ---------------------------------------------------------------------------
# Validação de campos obrigatórios
# ---------------------------------------------------------------------------


class TestSaveValidation:
    """Testa validação dos campos obrigatórios no endpoint /save."""

    def test_missing_name_returns_400(self, client):
        """Sem name deve retornar 400."""
        payload = _build_save_payload(name="")
        resp = client.post(SAVE_ENDPOINT, json=payload)
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()

    def test_whitespace_name_returns_400(self, client):
        """Name com apenas espaços deve retornar 400."""
        payload = _build_save_payload(name="   ")
        resp = client.post(SAVE_ENDPOINT, json=payload)
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()

    def test_missing_street_returns_400(self, client):
        """Sem street deve retornar 400."""
        payload = _build_save_payload(street="")
        resp = client.post(SAVE_ENDPOINT, json=payload)
        assert resp.status_code == 400
        assert "street" in resp.json()["detail"].lower()

    def test_whitespace_street_returns_400(self, client):
        """Street com apenas espaços deve retornar 400."""
        payload = _build_save_payload(street="   ")
        resp = client.post(SAVE_ENDPOINT, json=payload)
        assert resp.status_code == 400
        assert "street" in resp.json()["detail"].lower()

    def test_name_checked_before_street(self, client):
        """Se ambos name e street forem inválidos, name deve ser reportado primeiro."""
        payload = _build_save_payload(name="", street="")
        resp = client.post(SAVE_ENDPOINT, json=payload)
        assert resp.status_code == 400
        assert "name" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Caso de sucesso
# ---------------------------------------------------------------------------


class TestSaveSuccess:
    """Testa o fluxo de sucesso do endpoint /save."""

    @patch("app.routers.gc_image_import.GcImageSaveService")
    def test_valid_payload_returns_201(self, mock_service_class, client):
        """Payload válido deve retornar 201 com dados do GC."""
        payload = _build_save_payload()
        gc_mock = _build_gc_mock(payload)

        mock_service = MagicMock()
        mock_service.save = AsyncMock(return_value=gc_mock)
        mock_service_class.return_value = mock_service

        resp = client.post(SAVE_ENDPOINT, json=payload)
        assert resp.status_code == 201
        body = resp.json()
        assert body["data"]["name"] == payload["name"]
        assert body["message"]

    @patch("app.routers.gc_image_import.GcImageSaveService")
    def test_response_contains_gc_id(self, mock_service_class, client):
        """A resposta deve conter o id do GC criado."""
        payload = _build_save_payload()
        gc_mock = _build_gc_mock(payload)

        mock_service = MagicMock()
        mock_service.save = AsyncMock(return_value=gc_mock)
        mock_service_class.return_value = mock_service

        resp = client.post(SAVE_ENDPOINT, json=payload)
        assert resp.status_code == 201
        assert resp.json()["data"]["id"] == str(gc_mock.id)

    @patch("app.routers.gc_image_import.GcImageSaveService")
    def test_response_follows_api_response_pattern(self, mock_service_class, client):
        """A resposta deve seguir o padrão { data, message }."""
        payload = _build_save_payload()
        gc_mock = _build_gc_mock(payload)

        mock_service = MagicMock()
        mock_service.save = AsyncMock(return_value=gc_mock)
        mock_service_class.return_value = mock_service

        resp = client.post(SAVE_ENDPOINT, json=payload)
        body = resp.json()
        assert "data" in body
        assert "message" in body

    @patch("app.routers.gc_image_import.GcImageSaveService")
    def test_save_service_called_once(self, mock_service_class, client):
        """O serviço de salvamento deve ser chamado exatamente uma vez."""
        payload = _build_save_payload()
        gc_mock = _build_gc_mock(payload)

        mock_service = MagicMock()
        mock_service.save = AsyncMock(return_value=gc_mock)
        mock_service_class.return_value = mock_service

        client.post(SAVE_ENDPOINT, json=payload)
        mock_service.save.assert_awaited_once()

    @patch("app.routers.gc_image_import.GcImageSaveService")
    def test_minimal_payload_accepted(self, mock_service_class, client):
        """Payload com apenas campos obrigatórios (name, street) deve ser aceito."""
        payload = {
            "name": fake.company(),
            "street": fake.street_name(),
        }
        gc_mock = _build_gc_mock(payload)

        mock_service = MagicMock()
        mock_service.save = AsyncMock(return_value=gc_mock)
        mock_service_class.return_value = mock_service

        resp = client.post(SAVE_ENDPOINT, json=payload)
        assert resp.status_code == 201

    @patch("app.routers.gc_image_import.GcImageSaveService")
    def test_payload_with_leaders_and_meetings(self, mock_service_class, client):
        """Payload com líderes e encontros deve ser aceito."""
        payload = _build_save_payload(
            leaders=[
                {
                    "name": fake.name(),
                    "contacts": [
                        {"type": "whatsapp", "value": fake.phone_number()},
                    ],
                }
            ],
            meetings=[
                {
                    "weekday": fake.random_int(min=0, max=6),
                    "start_time": "19:30",
                    "notes": fake.sentence(),
                },
            ],
        )
        gc_mock = _build_gc_mock(payload)

        mock_service = MagicMock()
        mock_service.save = AsyncMock(return_value=gc_mock)
        mock_service_class.return_value = mock_service

        resp = client.post(SAVE_ENDPOINT, json=payload)
        assert resp.status_code == 201
