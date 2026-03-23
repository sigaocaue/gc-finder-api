"""Unit tests for public and authenticated leader endpoints."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.routers import leaders
from app.schemas.leader import LeaderCreate, LeaderUpdate


def build_leader(*, name="Líder", email="lider@example.com"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        display_name=name,
        bio="Bio",
        photo_url=None,
        is_active=True,
        contacts=[],
        created_at="2024-01-01T00:00:00",
    )


@pytest.mark.asyncio
@patch("app.routers.leaders.LeaderService")
async def test_list_leaders_returns_transformed_objects(mock_service):
    service = mock_service.return_value
    leader = build_leader(name="Ana")
    service.list_all = AsyncMock(return_value=[leader])

    response = await leaders.list_leaders(db=SimpleNamespace())

    assert response.message == "Lista de líderes"
    assert response.data[0].name == "Ana"
    service.list_all.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.routers.leaders.LeaderService")
async def test_get_leader_found(mock_service):
    service = mock_service.return_value
    leader = build_leader(name="Carlos")
    service.get_by_id = AsyncMock(return_value=leader)

    response = await leaders.get_leader("id", db=SimpleNamespace())

    assert response.message == "Líder encontrado"
    assert response.data.name == "Carlos"


@pytest.mark.asyncio
@patch("app.routers.leaders.LeaderService")
async def test_get_leader_not_found(mock_service):
    service = mock_service.return_value
    service.get_by_id = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await leaders.get_leader("missing", db=SimpleNamespace())

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
@patch("app.routers.leaders.LeaderService")
async def test_create_leader_success(mock_service):
    service = mock_service.return_value
    leader = build_leader(name="Nova")
    service.create = AsyncMock(return_value=leader)
    body = LeaderCreate(name="Nova", contacts=[])

    response = await leaders.create_leader(body, current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Líder criado com sucesso"
    assert response.data.name == "Nova"
    service.create.assert_awaited_once_with(body)


@pytest.mark.asyncio
@patch("app.routers.leaders.LeaderService")
async def test_update_leader_success(mock_service):
    service = mock_service.return_value
    leader = build_leader(name="Atualizado")
    service.update = AsyncMock(return_value=leader)
    body = LeaderUpdate(name="Atualizado")

    response = await leaders.update_leader("id", body, current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Líder atualizado com sucesso"
    assert response.data.name == "Atualizado"


@pytest.mark.asyncio
@patch("app.routers.leaders.LeaderService")
async def test_update_leader_not_found(mock_service):
    service = mock_service.return_value
    service.update = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await leaders.update_leader("id", LeaderUpdate(), current_user=SimpleNamespace(), db=SimpleNamespace())

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
@patch("app.routers.leaders.LeaderService")
async def test_deactivate_leader_success(mock_service):
    service = mock_service.return_value
    leader = build_leader(name="Desativado")
    service.deactivate = AsyncMock(return_value=leader)

    response = await leaders.deactivate_leader("id", current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Líder desativado com sucesso"
    assert response.data.name == "Desativado"


@pytest.mark.asyncio
@patch("app.routers.leaders.LeaderService")
async def test_deactivate_leader_not_found(mock_service):
    service = mock_service.return_value
    service.deactivate = AsyncMock(return_value=None)

    with pytest.raises(Exception) as excinfo:
        await leaders.deactivate_leader("id", current_user=SimpleNamespace(), db=SimpleNamespace())

    assert excinfo.value.status_code == 404
