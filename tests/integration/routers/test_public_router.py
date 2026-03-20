"""Testes das rotas públicas — mapa, proximidade e registro de interesse."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from faker import Faker

fake = Faker("pt_BR")

BASE = "/api/v1/public"


def _make_fake_map_item():
    """Cria mock compatível com GcMapItem.model_validate()."""
    item = MagicMock()
    item.id = uuid.uuid4()
    item.name = fake.company()
    item.latitude = float(fake.latitude())
    item.longitude = float(fake.longitude())
    item.neighborhood = fake.bairro()
    item.city = fake.city()
    return item


class TestGcsForMap:
    """Testa GET /api/v1/public/gcs/map."""

    @patch("app.routers.public.GcService")
    def test_gcs_for_map_success(self, MockService, client):
        """Deve retornar 200 com lista de GCs para o mapa."""
        mock_service = MockService.return_value
        mock_service.get_map_data = AsyncMock(return_value=[
            _make_fake_map_item(), _make_fake_map_item(),
        ])
        resp = client.get(f"{BASE}/gcs/map")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) == 2


class TestGcsNearby:
    """Testa GET /api/v1/public/gcs/nearby."""

    @patch("app.routers.public.GcService")
    def test_gcs_nearby_success(self, MockService, client):
        """Deve retornar 200 com lista de GCs próximos."""
        mock_service = MockService.return_value
        nearby_items = [
            {"id": str(uuid.uuid4()), "name": fake.company(),
             "latitude": -23.18, "longitude": -46.88,
             "neighborhood": fake.bairro(), "city": fake.city(),
             "distance_km": 1.5},
        ]
        mock_service.find_nearby = AsyncMock(return_value=nearby_items)
        resp = client.get(f"{BASE}/gcs/nearby", params={"zip_code": "13201000"})
        assert resp.status_code == 200


class TestRegisterInterest:
    """Testa POST /api/v1/public/interest."""

    @patch("app.routers.public.submit_interest", new_callable=AsyncMock)
    def test_register_interest_success(self, mock_submit, client):
        """Submissão bem-sucedida ao Google Forms deve retornar 201."""
        mock_submit.return_value = True
        resp = client.post(f"{BASE}/interest", json={
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "zip_code": fake.postcode(),
            "message": fake.sentence(),
        })
        assert resp.status_code == 201
        assert resp.json()["message"]

    @patch("app.routers.public.submit_interest", new_callable=AsyncMock)
    def test_register_interest_forms_failure(self, mock_submit, client):
        """Falha no Google Forms deve retornar 502."""
        mock_submit.return_value = False
        resp = client.post(f"{BASE}/interest", json={
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "zip_code": fake.postcode(),
        })
        assert resp.status_code == 502
