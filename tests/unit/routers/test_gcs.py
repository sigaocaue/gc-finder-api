"""Unit tests for the GC router endpoints."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.routers import gcs
from app.schemas.gc import GcCreate, GcLeaderLink, GcUpdate


def build_gc(name="GC Teste"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name=name,
        description="Desc",
        zip_code="01001-000",
        street="Rua ABC",
        number="123",
        complement=None,
        neighborhood="Centro",
        city="São Paulo",
        state="SP",
        latitude=-23.5,
        longitude=-46.6,
        is_active=True,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-02T00:00:00",
        leaders=[],
        meetings=[],
        medias=[],
    )


@pytest.mark.asyncio
@patch("app.routers.gcs.GcService")
async def test_list_gcs_uses_pagination(mock_service):
    service = mock_service.return_value
    service.list_all = AsyncMock(return_value=[build_gc()])

    response = await gcs.list_gcs(db=SimpleNamespace(), skip=5, limit=10)

    assert response.message == "Lista de GCs"
    assert response.data[0].name == "GC Teste"
    service.list_all.assert_awaited_once_with(skip=5, limit=10)


@pytest.mark.asyncio
@patch("app.routers.gcs.GcService")
async def test_get_gc_returns_data(mock_service):
    service = mock_service.return_value
    gc = build_gc()
    service.get_by_id = AsyncMock(return_value=gc)

    response = await gcs.get_gc(gc.id, db=SimpleNamespace())

    assert response.data.id == gc.id
    assert response.message == "GC encontrado"


@pytest.mark.asyncio
@patch("app.routers.gcs.GcService")
async def test_create_gc(mock_service):
    service = mock_service.return_value
    gc = build_gc()
    service.create = AsyncMock(return_value=gc)

    body = GcCreate(
        name="Novo GC",
        zip_code="01001000",
        street="Rua Teste",
        neighborhood="Centro",
        city="São Paulo",
        state="SP",
    )

    response = await gcs.create_gc(body, current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.data.name == "GC Teste"
    assert response.message == "GC criado com sucesso"
    service.create.assert_awaited_once_with(body)


@pytest.mark.asyncio
@patch("app.routers.gcs.GcService")
async def test_update_gc_success(mock_service):
    service = mock_service.return_value
    gc = build_gc()
    service.update = AsyncMock(return_value=gc)

    response = await gcs.update_gc("id", GcUpdate(name="Atualizado"), current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "GC atualizado com sucesso"
    assert response.data.name == "GC Teste"


@pytest.mark.asyncio
@patch("app.routers.gcs.GcService")
async def test_update_gc_not_found(mock_service):
    service = mock_service.return_value
    service.update = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as excinfo:
        await gcs.update_gc("missing", GcUpdate(), current_user=SimpleNamespace(), db=SimpleNamespace())

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
@patch("app.routers.gcs.GcService")
async def test_deactivate_gc_success(mock_service):
    service = mock_service.return_value
    gc = build_gc()
    service.deactivate = AsyncMock(return_value=gc)

    response = await gcs.deactivate_gc("id", current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "GC desativado com sucesso"


@pytest.mark.asyncio
@patch("app.routers.gcs.GcService")
async def test_deactivate_gc_not_found(mock_service):
    service = mock_service.return_value
    service.deactivate = AsyncMock(return_value=None)

    with pytest.raises(HTTPException) as excinfo:
        await gcs.deactivate_gc("id", current_user=SimpleNamespace(), db=SimpleNamespace())

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
@patch("app.routers.gcs.GcService")
async def test_link_leader(mock_service):
    service = mock_service.return_value
    gc = build_gc()
    service.link_leader = AsyncMock(return_value=gc)

    body = GcLeaderLink(leader_id=uuid.uuid4())
    response = await gcs.link_leader("id", body, current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Líder vinculado ao GC com sucesso"
    assert response.data.name == "GC Teste"


@pytest.mark.asyncio
@patch("app.routers.gcs.GcService")
async def test_unlink_leader(mock_service):
    service = mock_service.return_value
    service.unlink_leader = AsyncMock(return_value=None)

    response = await gcs.unlink_leader("id", uuid.uuid4(), current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Líder desvinculado do GC com sucesso"
