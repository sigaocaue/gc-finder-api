"""Testes de integração das rotas públicas (mapa e proximidade)."""

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from tests.integration.conftest import _auth_header


class TestGcsMap:
    """GET /api/v1/public/gcs/map"""

    async def test_map_empty(self, client):
        resp = await client.get("/api/v1/public/gcs/map")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    async def test_map_returns_gcs_with_coordinates(self, client, create_gc):
        gc = await create_gc(
            name="GC no Mapa",
            latitude=Decimal("-23.5505199"),
            longitude=Decimal("-46.6333094"),
        )
        resp = await client.get("/api/v1/public/gcs/map")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "GC no Mapa"
        assert data[0]["latitude"] is not None

    async def test_map_excludes_gcs_without_coordinates(self, client, create_gc):
        await create_gc(name="Sem Coords", latitude=None, longitude=None)
        await create_gc(
            name="Com Coords",
            latitude=Decimal("-23.55"),
            longitude=Decimal("-46.63"),
        )
        resp = await client.get("/api/v1/public/gcs/map")
        data = resp.json()["data"]
        assert len(data) == 1
        assert data[0]["name"] == "Com Coords"


class TestGcsNearby:
    """GET /api/v1/public/gcs/nearby?zip_code=..."""

    async def test_nearby_returns_sorted_by_distance(self, client, create_gc):
        # Cria 2 GCs com coordenadas diferentes
        await create_gc(
            name="GC Perto",
            latitude=Decimal("-23.5505"),
            longitude=Decimal("-46.6333"),
        )
        await create_gc(
            name="GC Longe",
            latitude=Decimal("-22.9068"),
            longitude=Decimal("-43.1729"),
        )

        with (
            patch(
                "app.services.gc_service.fetch_address_from_cep",
                new_callable=AsyncMock,
                return_value={
                    "street": "Praça da Sé",
                    "neighborhood": "Sé",
                    "city": "São Paulo",
                    "state": "SP",
                },
            ),
            patch(
                "app.services.gc_service.fetch_coordinates",
                new_callable=AsyncMock,
                return_value=(-23.5505, -46.6333),
            ),
        ):
            resp = await client.get("/api/v1/public/gcs/nearby?zip_code=01001000")

        assert resp.status_code == 200
        data = resp.json()["data"]
        assert len(data) == 2
        assert data[0]["name"] == "GC Perto"
        assert data[0]["distance_km"] <= data[1]["distance_km"]

    async def test_nearby_geocode_failure(self, client):
        with (
            patch(
                "app.services.gc_service.fetch_address_from_cep",
                new_callable=AsyncMock,
                return_value={
                    "street": "Rua X",
                    "neighborhood": "Y",
                    "city": "Z",
                    "state": "AA",
                },
            ),
            patch(
                "app.services.gc_service.fetch_coordinates",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            resp = await client.get("/api/v1/public/gcs/nearby?zip_code=00000000")

        assert resp.status_code == 400


class TestRegisterInterest:
    """POST /api/v1/public/interest"""

    async def test_register_interest_success(self, client):
        with patch(
            "app.routers.public.submit_interest",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.post("/api/v1/public/interest", json={
                "name": "João Silva",
                "email": "joao@email.com",
                "phone": "11999999999",
                "zip_code": "01001000",
                "message": "Gostaria de participar",
            })
        assert resp.status_code == 201
        assert resp.json()["message"] == "Interesse registrado com sucesso"

    async def test_register_interest_form_failure(self, client):
        with patch(
            "app.routers.public.submit_interest",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client.post("/api/v1/public/interest", json={
                "name": "Maria",
                "email": "maria@email.com",
                "phone": "11888888888",
                "zip_code": "01001000",
            })
        assert resp.status_code == 502
