"""Testes das rotas de autenticação POST /login, /refresh, /logout e GET /me."""

from unittest.mock import AsyncMock, MagicMock, patch

from faker import Faker

fake = Faker()

BASE = "/api/v1/auth"


class TestLogin:
    """Testa o endpoint POST /login."""

    @patch("app.routers.auth.AuthService")
    def test_login_success(self, MockService, client):
        """Credenciais válidas devem retornar 200 com tokens."""
        mock_service = MockService.return_value
        mock_service.login = AsyncMock(return_value={
            "access_token": fake.sha256(),
            "refresh_token": fake.sha256(),
            "token_type": "bearer",
            "expires_in": 900,
        })
        resp = client.post(f"{BASE}/login", json={
            "email": fake.email(),
            "password": fake.password(),
        })
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]
        assert body["message"]

    @patch("app.routers.auth.AuthService")
    def test_login_invalid_credentials(self, MockService, client):
        """Credenciais inválidas devem retornar 401."""
        mock_service = MockService.return_value
        mock_service.login = AsyncMock(return_value=None)
        resp = client.post(f"{BASE}/login", json={
            "email": fake.email(),
            "password": fake.password(),
        })
        assert resp.status_code == 401


class TestRefresh:
    """Testa o endpoint POST /refresh."""

    @patch("app.routers.auth.AuthService")
    def test_refresh_success(self, MockService, client):
        """Refresh token válido deve retornar 200 com novos tokens."""
        mock_service = MockService.return_value
        mock_service.refresh = AsyncMock(return_value={
            "access_token": fake.sha256(),
            "refresh_token": fake.sha256(),
            "token_type": "bearer",
            "expires_in": 900,
        })
        resp = client.post(f"{BASE}/refresh", json={
            "refresh_token": fake.sha256(),
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()["data"]

    @patch("app.routers.auth.AuthService")
    def test_refresh_invalid_token(self, MockService, client):
        """Refresh token inválido deve retornar 401."""
        mock_service = MockService.return_value
        mock_service.refresh = AsyncMock(return_value=None)
        resp = client.post(f"{BASE}/refresh", json={
            "refresh_token": fake.sha256(),
        })
        assert resp.status_code == 401


class TestLogout:
    """Testa o endpoint POST /logout."""

    @patch("app.routers.auth.AuthService")
    def test_logout_success(self, MockService, client):
        """Logout deve retornar 200."""
        mock_service = MockService.return_value
        mock_service.logout = AsyncMock()
        resp = client.post(f"{BASE}/logout", json={
            "refresh_token": fake.sha256(),
        })
        assert resp.status_code == 200
        assert resp.json()["message"]


class TestMe:
    """Testa o endpoint GET /me."""

    def test_me_success(self, client, fake_user):
        """Deve retornar dados do usuário autenticado."""
        resp = client.get(f"{BASE}/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"]["email"] == fake_user.email
        assert body["data"]["name"] == fake_user.name
        assert body["data"]["role"] == "editor"
