"""Testes das rotas de líderes — listagem pública e CRUD autenticado."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from faker import Faker

from app.models.leader import Leader

fake = Faker()

BASE = "/api/v1/leaders"


def _make_fake_leader(**overrides):
    """Cria mock de Leader compatível com LeaderResponse.model_validate()."""
    leader = MagicMock(spec=Leader)
    leader.id = overrides.get("id", uuid.uuid4())
    leader.name = overrides.get("name", fake.name())
    leader.display_name = overrides.get("display_name", None)
    leader.bio = overrides.get("bio", fake.sentence())
    leader.photo_url = overrides.get("photo_url", fake.image_url())
    leader.is_active = overrides.get("is_active", True)
    leader.contacts = overrides.get("contacts", [])
    leader.created_at = overrides.get("created_at", datetime.now())
    return leader


class TestListLeaders:
    """Testa GET /api/v1/leaders/ (pública)."""

    @patch("app.routers.leaders.LeaderService")
    def test_list_leaders_success(self, MockService, client):
        """Deve retornar 200 com lista de líderes."""
        mock_service = MockService.return_value
        mock_service.list_all = AsyncMock(return_value=[
            _make_fake_leader(), _make_fake_leader(),
        ])
        resp = client.get(f"{BASE}/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2


class TestGetLeader:
    """Testa GET /api/v1/leaders/{leader_id} (pública)."""

    @patch("app.routers.leaders.LeaderService")
    def test_get_leader_success(self, MockService, client):
        """Líder existente deve retornar 200."""
        leader = _make_fake_leader()
        mock_service = MockService.return_value
        mock_service.get_by_id = AsyncMock(return_value=leader)
        resp = client.get(f"{BASE}/{leader.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == str(leader.id)

    @patch("app.routers.leaders.LeaderService")
    def test_get_leader_not_found(self, MockService, client):
        """Líder inexistente deve retornar 404."""
        mock_service = MockService.return_value
        mock_service.get_by_id = AsyncMock(return_value=None)
        resp = client.get(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestCreateLeader:
    """Testa POST /api/v1/leaders/ (autenticada)."""

    @patch("app.routers.leaders.LeaderService")
    def test_create_leader_success(self, MockService, client):
        """Payload válido deve retornar 201."""
        leader = _make_fake_leader()
        mock_service = MockService.return_value
        mock_service.create = AsyncMock(return_value=leader)
        resp = client.post(f"{BASE}/", json={
            "name": fake.name(),
            "bio": fake.sentence(),
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["id"] == str(leader.id)


class TestUpdateLeader:
    """Testa PUT /api/v1/leaders/{leader_id} (autenticada)."""

    @patch("app.routers.leaders.LeaderService")
    def test_update_leader_success(self, MockService, client):
        """Atualização com sucesso deve retornar 200."""
        leader = _make_fake_leader()
        mock_service = MockService.return_value
        mock_service.update = AsyncMock(return_value=leader)
        resp = client.put(f"{BASE}/{leader.id}", json={
            "name": fake.name(),
        })
        assert resp.status_code == 200

    @patch("app.routers.leaders.LeaderService")
    def test_update_leader_not_found(self, MockService, client):
        """Líder inexistente deve retornar 404."""
        mock_service = MockService.return_value
        mock_service.update = AsyncMock(return_value=None)
        resp = client.put(f"{BASE}/{uuid.uuid4()}", json={
            "name": fake.name(),
        })
        assert resp.status_code == 404


class TestDeactivateLeader:
    """Testa DELETE /api/v1/leaders/{leader_id} (autenticada)."""

    @patch("app.routers.leaders.LeaderService")
    def test_deactivate_leader_success(self, MockService, client):
        """Desativação com sucesso deve retornar 200."""
        leader = _make_fake_leader(is_active=False)
        mock_service = MockService.return_value
        mock_service.deactivate = AsyncMock(return_value=leader)
        resp = client.delete(f"{BASE}/{leader.id}")
        assert resp.status_code == 200

    @patch("app.routers.leaders.LeaderService")
    def test_deactivate_leader_not_found(self, MockService, client):
        """Líder inexistente deve retornar 404."""
        mock_service = MockService.return_value
        mock_service.deactivate = AsyncMock(return_value=None)
        resp = client.delete(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404
