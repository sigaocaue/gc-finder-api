"""Unit tests for the public router endpoints."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.schemas.public import InterestRequest
from app.routers import public


@pytest.mark.asyncio
@patch("app.routers.public.GcService")
async def test_gcs_for_map_validates_items(mock_service):
    items = [
        SimpleNamespace(
            id=uuid.uuid4(),
            name="GC Bairro Alto",
            latitude=-23.5,
            longitude=-46.6,
            neighborhood="Centro",
            city="São Paulo",
        )
    ]
    service = mock_service.return_value
    service.get_map_data = AsyncMock(return_value=items)

    response = await public.gcs_for_map(db=SimpleNamespace())

    assert response.message == "GCs para o mapa"
    assert response.data[0].name == items[0].name
    assert response.data[0].id == items[0].id
    assert response.data[0].latitude == items[0].latitude
    service.get_map_data.assert_awaited_once()


@pytest.mark.asyncio
@patch("app.routers.public.GcService")
async def test_gcs_nearby_returns_service_list(mock_service):
    nearby_items = [
        {"id": uuid.uuid4(), "distance_km": 1.5},
        {"id": uuid.uuid4(), "distance_km": 2.0},
    ]
    service = mock_service.return_value
    service.find_nearby = AsyncMock(return_value=nearby_items)

    response = await public.gcs_nearby(db=SimpleNamespace(), zip_code="12345678")

    assert response.message == "GCs próximos encontrados"
    assert response.data == nearby_items
    service.find_nearby.assert_awaited_once_with("12345678")


@pytest.mark.asyncio
@patch("app.routers.public.submit_interest", new_callable=AsyncMock)
async def test_register_interest_success(mock_submit):
    body = InterestRequest(
        name="Visitante",
        email="visitante@example.com",
        phone="(11) 99999-0000",
        zip_code="01234567",
        message="Quero receber novidades",
    )
    mock_submit.return_value = True

    response = await public.register_interest(body, db=SimpleNamespace())

    mock_submit.assert_awaited_once_with(
        name="Visitante",
        email="visitante@example.com",
        phone="(11) 99999-0000",
        zip_code="01234567",
        message="Quero receber novidades",
    )
    assert response.message == "Interesse registrado com sucesso"


@pytest.mark.asyncio
@patch("app.routers.public.submit_interest", new_callable=AsyncMock)
async def test_register_interest_failure_raises(mock_submit):
    body = InterestRequest(
        name="Outro",
        email="outro@example.com",
        phone="(21) 88888-0000",
        zip_code="87654321",
        message="Preciso de ajuda",
    )
    mock_submit.return_value = False

    with pytest.raises(HTTPException) as excinfo:
        await public.register_interest(body, db=SimpleNamespace())

    assert excinfo.value.status_code == 502
    assert "Falha ao enviar dados" in excinfo.value.detail
