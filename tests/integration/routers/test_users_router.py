"""Testes das rotas de usuários (CRUD) — requer AdminUser."""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from faker import Faker

from app.models.user import User

fake = Faker()

BASE = "/api/v1/users"


def _make_fake_user(**overrides):
    """Cria mock de User compatível com UserResponse.model_validate()."""
    user = MagicMock(spec=User)
    user.id = overrides.get("id", uuid.uuid4())
    user.name = overrides.get("name", fake.name())
    user.email = overrides.get("email", fake.email())
    user.role = overrides.get("role", "editor")
    user.is_active = overrides.get("is_active", True)
    user.created_at = overrides.get("created_at", datetime.now())
    return user


class TestListUsers:
    """Testa GET /api/v1/users/."""

    @patch("app.routers.users.UserService")
    def test_list_users_success(self, MockService, admin_client):
        """Deve retornar 200 com lista de usuários."""
        mock_service = MockService.return_value
        mock_service.list_all = AsyncMock(return_value=[
            _make_fake_user(), _make_fake_user(),
        ])
        resp = admin_client.get(f"{BASE}/")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2


class TestGetUser:
    """Testa GET /api/v1/users/{user_id}."""

    @patch("app.routers.users.UserService")
    def test_get_user_success(self, MockService, admin_client):
        """Usuário existente deve retornar 200."""
        user = _make_fake_user()
        mock_service = MockService.return_value
        mock_service.get_by_id = AsyncMock(return_value=user)
        resp = admin_client.get(f"{BASE}/{user.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == str(user.id)

    @patch("app.routers.users.UserService")
    def test_get_user_not_found(self, MockService, admin_client):
        """Usuário inexistente deve retornar 404."""
        mock_service = MockService.return_value
        mock_service.get_by_id = AsyncMock(return_value=None)
        resp = admin_client.get(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestCreateUser:
    """Testa POST /api/v1/users/."""

    @patch("app.routers.users.UserService")
    def test_create_user_success(self, MockService, admin_client):
        """Payload válido deve retornar 201."""
        user = _make_fake_user()
        mock_service = MockService.return_value
        mock_service.create = AsyncMock(return_value=user)
        resp = admin_client.post(f"{BASE}/", json={
            "name": fake.name(),
            "email": fake.email(),
            "password": fake.password(),
            "role": "editor",
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["id"] == str(user.id)


class TestUpdateUser:
    """Testa PUT /api/v1/users/{user_id}."""

    @patch("app.routers.users.UserService")
    def test_update_user_success(self, MockService, admin_client):
        """Atualização com sucesso deve retornar 200."""
        user = _make_fake_user()
        mock_service = MockService.return_value
        mock_service.update = AsyncMock(return_value=user)
        resp = admin_client.put(f"{BASE}/{user.id}", json={
            "name": fake.name(),
        })
        assert resp.status_code == 200

    @patch("app.routers.users.UserService")
    def test_update_user_not_found(self, MockService, admin_client):
        """Usuário inexistente deve retornar 404."""
        mock_service = MockService.return_value
        mock_service.update = AsyncMock(return_value=None)
        resp = admin_client.put(f"{BASE}/{uuid.uuid4()}", json={
            "name": fake.name(),
        })
        assert resp.status_code == 404


class TestDeactivateUser:
    """Testa DELETE /api/v1/users/{user_id}."""

    @patch("app.routers.users.UserService")
    def test_deactivate_user_success(self, MockService, admin_client):
        """Desativação com sucesso deve retornar 200."""
        user = _make_fake_user(is_active=False)
        mock_service = MockService.return_value
        mock_service.deactivate = AsyncMock(return_value=user)
        resp = admin_client.delete(f"{BASE}/{user.id}")
        assert resp.status_code == 200

    @patch("app.routers.users.UserService")
    def test_deactivate_user_not_found(self, MockService, admin_client):
        """Usuário inexistente deve retornar 404."""
        mock_service = MockService.return_value
        mock_service.deactivate = AsyncMock(return_value=None)
        resp = admin_client.delete(f"{BASE}/{uuid.uuid4()}")
        assert resp.status_code == 404
