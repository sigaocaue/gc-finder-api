"""Testes de integração do CRUD de líderes."""

import uuid

import pytest

from tests.integration.conftest import _auth_header


class TestListLeaders:
    """GET /api/v1/leaders/ — rota pública"""

    async def test_list_leaders_empty(self, client):
        resp = await client.get("/api/v1/leaders/")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_list_leaders_returns_active_only(self, client, create_leader):
        active = await create_leader(name="Active Leader")
        inactive = await create_leader(name="Inactive Leader", is_active=False)

        resp = await client.get("/api/v1/leaders/")
        assert resp.status_code == 200
        names = [l["name"] for l in resp.json()["data"]]
        assert "Active Leader" in names
        assert "Inactive Leader" not in names


class TestGetLeader:
    """GET /api/v1/leaders/{leader_id} — rota pública"""

    async def test_get_leader(self, client, create_leader):
        leader = await create_leader(name="Test Leader")
        resp = await client.get(f"/api/v1/leaders/{leader.id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Test Leader"

    async def test_get_leader_not_found(self, client):
        resp = await client.get(f"/api/v1/leaders/{uuid.uuid4()}")
        assert resp.status_code == 404


class TestCreateLeader:
    """POST /api/v1/leaders/ — autenticado"""

    async def test_create_leader_with_contacts(self, client, editor_user, editor_token):
        resp = await client.post("/api/v1/leaders/", headers=_auth_header(editor_token), json={
            "name": "New Leader",
            "bio": "Líder de teste",
            "contacts": [
                {"type": "whatsapp", "value": "+5511999999999"},
                {"type": "instagram", "value": "@newleader"},
            ],
        })
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["name"] == "New Leader"
        assert len(data["contacts"]) == 2

    async def test_create_leader_without_auth_returns_401(self, client):
        resp = await client.post("/api/v1/leaders/", json={"name": "No Auth"})
        assert resp.status_code in (401, 403)

    async def test_create_leader_no_contacts(self, client, editor_user, editor_token):
        resp = await client.post("/api/v1/leaders/", headers=_auth_header(editor_token), json={
            "name": "Simple Leader",
        })
        assert resp.status_code == 201
        assert resp.json()["data"]["contacts"] == []


class TestUpdateLeader:
    """PUT /api/v1/leaders/{leader_id} — autenticado"""

    async def test_update_leader(self, client, create_leader, editor_user, editor_token):
        leader = await create_leader()
        resp = await client.put(
            f"/api/v1/leaders/{leader.id}",
            headers=_auth_header(editor_token),
            json={"name": "Updated Name", "bio": "New bio"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Updated Name"


class TestDeactivateLeader:
    """DELETE /api/v1/leaders/{leader_id} — autenticado"""

    async def test_deactivate_leader(self, client, create_leader, editor_user, editor_token):
        leader = await create_leader()
        resp = await client.delete(
            f"/api/v1/leaders/{leader.id}",
            headers=_auth_header(editor_token),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["is_active"] is False

    async def test_deactivated_leader_not_in_list(self, client, create_leader, editor_user, editor_token):
        leader = await create_leader(name="To Deactivate")
        await client.delete(
            f"/api/v1/leaders/{leader.id}",
            headers=_auth_header(editor_token),
        )

        resp = await client.get("/api/v1/leaders/")
        names = [l["name"] for l in resp.json()["data"]]
        assert "To Deactivate" not in names
