"""Unit tests for GC medias router endpoints."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.routers import gc_medias
from app.schemas.gc_media import GcMediaCreate, GcMediaUpdate


def build_media():
    return SimpleNamespace(
        id=uuid.uuid4(),
        gc_id=uuid.uuid4(),
        type="image",
        url="https://example.com/img.jpg",
        caption="Foto",
        display_order=0,
        created_at="2024-01-01T00:00:00",
    )


@pytest.mark.asyncio
@patch("app.routers.gc_medias.GcService")
async def test_list_medias_returns_entries(mock_service):
    service = mock_service.return_value
    medias = [build_media()]
    service.list_medias = AsyncMock(return_value=medias)

    response = await gc_medias.list_medias("gc-id", db=SimpleNamespace())

    assert response.message == "Lista de mídias"
    assert response.data[0].url == medias[0].url
    service.list_medias.assert_awaited_once_with("gc-id")


@pytest.mark.asyncio
@patch("app.routers.gc_medias.GcService")
async def test_create_media(mock_service):
    service = mock_service.return_value
    media = build_media()
    service.create_media = AsyncMock(return_value=media)
    body = GcMediaCreate(type="image", url="https://img", display_order=1)

    response = await gc_medias.create_media("gc-id", body, current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Mídia criada com sucesso"
    assert response.data.id == media.id
    service.create_media.assert_awaited_once_with("gc-id", body)


@pytest.mark.asyncio
@patch("app.routers.gc_medias.GcService")
async def test_update_media(mock_service):
    service = mock_service.return_value
    media = build_media()
    service.update_media = AsyncMock(return_value=media)
    body = GcMediaUpdate(caption="Atualizada")

    response = await gc_medias.update_media("gc-id", "media-id", body, current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Mídia atualizada com sucesso"
    assert response.data.caption == "Foto"
    service.update_media.assert_awaited_once_with("gc-id", "media-id", body)


@pytest.mark.asyncio
@patch("app.routers.gc_medias.GcService")
async def test_delete_media(mock_service):
    service = mock_service.return_value
    service.delete_media = AsyncMock(return_value=None)

    response = await gc_medias.delete_media("gc-id", "media-id", current_user=SimpleNamespace(), db=SimpleNamespace())

    assert response.message == "Mídia removida com sucesso"
    service.delete_media.assert_awaited_once_with("gc-id", "media-id")
