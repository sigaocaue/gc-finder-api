"""Testes de integração do fluxo de autenticação (login → refresh → logout → me)."""

import pytest

from tests.integration.conftest import _auth_header


class TestLogin:
    """POST /api/v1/auth/login"""

    async def test_login_success(self, client, admin_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123",
        })
        assert resp.status_code == 200
        body = resp.json()
        assert body["message"] == "Login realizado com sucesso"
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]
        assert body["data"]["token_type"] == "bearer"

    async def test_login_wrong_password(self, client, admin_user):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "wrong",
        })
        assert resp.status_code == 401

    async def test_login_nonexistent_email(self, client):
        resp = await client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "any",
        })
        assert resp.status_code == 401


class TestRefreshToken:
    """POST /api/v1/auth/refresh"""

    async def test_refresh_rotates_tokens(self, client, admin_user):
        # Faz login para obter o refresh token
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123",
        })
        refresh_token = login_resp.json()["data"]["refresh_token"]

        # Usa o refresh token para obter novos tokens
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 200
        new_data = resp.json()["data"]
        # O refresh token deve ser diferente (tem jti único)
        assert new_data["refresh_token"] != refresh_token
        assert "access_token" in new_data
        assert new_data["token_type"] == "bearer"

    async def test_refresh_reused_token_is_rejected(self, client, admin_user):
        """Token já rotacionado deve ser rejeitado."""
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123",
        })
        old_refresh = login_resp.json()["data"]["refresh_token"]

        # Primeira rotação — ok
        await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})

        # Segunda tentativa com o mesmo token — deve falhar
        resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
        assert resp.status_code == 401

    async def test_refresh_invalid_token(self, client):
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": "invalid.token.here",
        })
        assert resp.status_code == 401


class TestLogout:
    """POST /api/v1/auth/logout"""

    async def test_logout_revokes_refresh_token(self, client, admin_user):
        login_resp = await client.post("/api/v1/auth/login", json={
            "email": "admin@test.com",
            "password": "admin123",
        })
        data = login_resp.json()["data"]
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # Faz logout
        resp = await client.post(
            "/api/v1/auth/logout",
            json={"refresh_token": refresh_token},
            headers=_auth_header(access_token),
        )
        assert resp.status_code == 200

        # Tenta usar o refresh token revogado
        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh_token,
        })
        assert resp.status_code == 401


class TestMe:
    """GET /api/v1/auth/me"""

    async def test_me_returns_user_data(self, client, admin_user, admin_token):
        resp = await client.get("/api/v1/auth/me", headers=_auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    async def test_me_without_token_returns_401(self, client):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code in (401, 403)
