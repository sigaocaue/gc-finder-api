"""Testes de integração do CRUD de usuários (requer admin)."""

import uuid

import pytest

from tests.integration.conftest import _auth_header


class TestListUsers:
    """GET /api/v1/users/"""

    async def test_list_users_as_admin(self, client, admin_user, admin_token):
        resp = await client.get("/api/v1/users/", headers=_auth_header(admin_token))
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) >= 1
        emails = [u["email"] for u in data]
        assert "admin@test.com" in emails

    async def test_list_users_as_editor_returns_403(self, client, editor_user, editor_token):
        resp = await client.get("/api/v1/users/", headers=_auth_header(editor_token))
        assert resp.status_code == 403


class TestCreateUser:
    """POST /api/v1/users/"""

    async def test_create_user(self, client, admin_user, admin_token):
        resp = await client.post("/api/v1/users/", headers=_auth_header(admin_token), json={
            "name": "New User",
            "email": "newuser@test.com",
            "password": "secret123",
            "role": "editor",
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "editor"
        assert data["is_active"] is True
        assert "password" not in data
        assert "password_hash" not in data

    async def test_create_user_duplicate_email(self, client, admin_user, admin_token):
        resp = await client.post("/api/v1/users/", headers=_auth_header(admin_token), json={
            "name": "Duplicate",
            "email": "admin@test.com",
            "password": "secret123",
        })
        assert resp.status_code == 409


class TestGetUser:
    """GET /api/v1/users/{user_id}"""

    async def test_get_user_by_id(self, client, admin_user, admin_token):
        resp = await client.get(
            f"/api/v1/users/{admin_user.id}",
            headers=_auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["email"] == "admin@test.com"

    async def test_get_user_not_found(self, client, admin_user, admin_token):
        fake_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/users/{fake_id}",
            headers=_auth_header(admin_token),
        )
        assert resp.status_code == 404


class TestUpdateUser:
    """PUT /api/v1/users/{user_id}"""

    async def test_update_user_name(self, client, admin_user, admin_token):
        resp = await client.put(
            f"/api/v1/users/{admin_user.id}",
            headers=_auth_header(admin_token),
            json={"name": "Admin Updated"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Admin Updated"

    async def test_update_user_email_to_existing_email(self, client, admin_user, editor_user, admin_token):
        resp = await client.put(
            f"/api/v1/users/{admin_user.id}",
            headers=_auth_header(admin_token),
            json={"email": "editor@test.com"},
        )
        assert resp.status_code == 409


class TestDeactivateUser:
    """DELETE /api/v1/users/{user_id}"""

    async def test_deactivate_user(self, client, admin_user, editor_user, admin_token):
        resp = await client.delete(
            f"/api/v1/users/{editor_user.id}",
            headers=_auth_header(admin_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_active"] is False

    async def test_deactivated_user_cannot_login(self, client, admin_user, editor_user, admin_token):
        # Desativa o editor
        await client.delete(
            f"/api/v1/users/{editor_user.id}",
            headers=_auth_header(admin_token),
        )

        # Tenta fazer login com o editor desativado
        resp = await client.post("/api/v1/auth/login", json={
            "email": "editor@test.com",
            "password": "editor123",
        })
        assert resp.status_code == 403
