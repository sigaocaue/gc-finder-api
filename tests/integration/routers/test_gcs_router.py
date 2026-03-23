"""Testes das rotas de GCs — listagem pública, CRUD autenticado e vínculo de líderes."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from faker import Faker

from app.models.gc import Gc

fake = Faker("pt_BR")

BASE = "/api/v1/gcs"


def _make_fake_gc(**overrides):
    """Cria mock de Gc compatível com GcResponse.model_validate()."""
    gc = MagicMock(spec=Gc)
    gc.id = overrides.get("id", uuid.uuid4())
    gc.name = overrides.get("name", fake.company())
    gc.description = overrides.get("description", fake.sentence())
    gc.zip_code = overrides.get("zip_code", fake.postcode().replace("-", ""))
    gc.street = overrides.get("street", fake.street_name())
    gc.number = overrides.get("number", fake.building_number())
    gc.complement = overrides.get("complement", None)
    gc.neighborhood = overrides.get("neighborhood", fake.bairro())
    gc.city = overrides.get("city", fake.city())
    gc.state = overrides.get("state", fake.state_abbr())
    gc.latitude = overrides.get("latitude", float(fake.latitude()))
    gc.longitude = overrides.get("longitude", float(fake.longitude()))
    gc.is_active = overrides.get("is_active", True)
    gc.created_at = overrides.get("created_at", datetime.now())
    gc.updated_at = overrides.get("updated_at", datetime.now())
    gc.leader_associations = overrides.get("leader_associations", [])
    gc.meetings = overrides.get("meetings", [])
    gc.medias = overrides.get("medias", [])
    return gc


def _gc_as_dict(gc_mock):
    """Converte mock de Gc para dict compatível com GcResponse (para rota get_gc)."""
    return {
        "id": str(gc_mock.id),
        "name": gc_mock.name,
        "description": gc_mock.description,
        "zip_code": gc_mock.zip_code,
        "street": gc_mock.street,
        "number": gc_mock.number,
        "complement": gc_mock.complement,
        "neighborhood": gc_mock.neighborhood,
        "city": gc_mock.city,
        "state": gc_mock.state,
        "latitude": gc_mock.latitude,
        "longitude": gc_mock.longitude,
        "is_active": gc_mock.is_active,
        "created_at": gc_mock.created_at.isoformat(),
        "updated_at": gc_mock.updated_at.isoformat(),
        "leaders": [],
        "meetings": [],
        "medias": [],
    }


class TestListGcs:
    """Testa GET /api/v1/gcs/."""

    @patch("app.routers.gcs.GcService")
    def test_list_gcs_success(self, MockService, client):
        """Deve retornar 200 com lista de GCs."""
        mock_service = MockService.return_value
        mock_service.list_all = AsyncMock(return_value=[
            _make_fake_gc(), _make_fake_gc(),
        ])
        resp = client.get(f"{BASE}/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2

    @patch("app.routers.gcs.GcService")
    def test_list_gcs_with_pagination(self, MockService, client):
        """Deve passar parâmetros skip e limit ao serviço."""
        mock_service = MockService.return_value
        mock_service.list_all = AsyncMock(return_value=[])
        client.get(f"{BASE}/?skip=10&limit=5")
        mock_service.list_all.assert_awaited_once_with(skip=10, limit=5)


class TestGetGc:
    """Testa GET /api/v1/gcs/{gc_id}."""

    @patch("app.routers.gcs.GcService")
    def test_get_gc_success(self, MockService, client):
        """GC existente deve retornar 200."""
        gc = _make_fake_gc()
        mock_service = MockService.return_value
        mock_service.get_by_id = AsyncMock(return_value=_gc_as_dict(gc))
        resp = client.get(f"{BASE}/{gc.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == gc.name


class TestCreateGc:
    """Testa POST /api/v1/gcs/."""

    @patch("app.routers.gcs.GcService")
    def test_create_gc_success(self, MockService, client):
        """Payload válido deve retornar 201."""
        gc = _make_fake_gc()
        mock_service = MockService.return_value
        mock_service.create = AsyncMock(return_value=gc)
        resp = client.post(f"{BASE}/", json={
            "name": fake.company(),
            "zip_code": "13201000",
            "street": fake.street_name(),
            "neighborhood": fake.bairro(),
            "city": fake.city(),
            "state": "SP",
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["id"] == str(gc.id)


class TestUpdateGc:
    """Testa PUT /api/v1/gcs/{gc_id}."""

    @patch("app.routers.gcs.GcService")
    def test_update_gc_success(self, MockService, client):
        """Atualização com sucesso deve retornar 200."""
        gc = _make_fake_gc()
        mock_service = MockService.return_value
        mock_service.update = AsyncMock(return_value=gc)
        resp = client.put(f"{BASE}/{gc.id}", json={
            "name": fake.company(),
        })
        assert resp.status_code == 200

    @patch("app.routers.gcs.GcService")
    def test_update_gc_not_found(self, MockService, client):
        """GC inexistente deve retornar 404."""
        mock_service = MockService.return_value
        mock_service.update = AsyncMock(return_value=None)
        resp = client.put(f"{BASE}/{uuid.uuid4()}", json={
            "name": fake.company(),
        })
        assert resp.status_code == 404


class TestDeactivateGc:
    """Testa DELETE /api/v1/gcs/{gc_id}."""

    @patch("app.routers.gcs.GcService")
    def test_deactivate_gc_success(self, MockService, client):
        """Desativação com sucesso deve retornar 200."""
        gc = _make_fake_gc(is_active=False)
        mock_service = MockService.return_value
        mock_service.deactivate = AsyncMock(return_value=gc)
        resp = client.delete(f"{BASE}/{gc.id}")
        assert resp.status_code == 200

    @patch("app.routers.gcs.GcService")
    def test_deactivate_gc_not_found(self, MockService, client):
        """GC inexistente deve retornar 404."""
        mock_service = MockService.return_value
        mock_service.deactivate = AsyncMock(return_value=None)
        resp = client.delete(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestLinkLeader:
    """Testa POST /api/v1/gcs/{gc_id}/leaders."""

    @patch("app.routers.gcs.GcService")
    def test_link_leader_success(self, MockService, client):
        """Vincular líder deve retornar 201."""
        gc = _make_fake_gc()
        mock_service = MockService.return_value
        mock_service.link_leader = AsyncMock(return_value=gc)
        leader_id = uuid.uuid4()
        resp = client.post(f"{BASE}/{gc.id}/leaders", json={
            "leader_id": str(leader_id),
        })
        assert resp.status_code == 201


class TestUnlinkLeader:
    """Testa DELETE /api/v1/gcs/{gc_id}/leaders/{leader_id}."""

    @patch("app.routers.gcs.GcService")
    def test_unlink_leader_success(self, MockService, client):
        """Desvincular líder deve retornar 200."""
        mock_service = MockService.return_value
        mock_service.unlink_leader = AsyncMock()
        gc_id = uuid.uuid4()
        leader_id = uuid.uuid4()
        resp = client.delete(f"{BASE}/{gc_id}/leaders/{leader_id}")
        assert resp.status_code == 200
        assert resp.json()["message"]
