"""Unit tests for the geocoding helpers."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import geocoding_service


def _mock_async_client(monkeypatch, *, response_json=None, raise_exc=None, get_exc=None):
    """Configura um AsyncClient fake para retornar um JSON ou simular erros."""
    client = AsyncMock()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    if raise_exc:
        response.raise_for_status.side_effect = raise_exc
    response.json.return_value = response_json or {}

    if get_exc:
        client.get.side_effect = get_exc
    else:
        client.get.return_value = response

    ctx = AsyncMock()
    ctx.__aenter__.return_value = client
    ctx.__aexit__.return_value = False

    monkeypatch.setattr(geocoding_service.httpx, "AsyncClient", MagicMock(return_value=ctx))
    return response


@pytest.mark.asyncio
@patch("app.services.geocoding_service.sanitize_cep")
async def test_fetch_address_from_cep_success(sanitize_cep, monkeypatch):
    sanitize_cep.return_value = "01001000"

    payload = {"logradouro": "Praça da Sé", "bairro": "Centro", "localidade": "São Paulo", "uf": "SP"}
    _mock_async_client(monkeypatch, response_json=payload)

    result = await geocoding_service.fetch_address_from_cep("01.001-000")

    assert result == {
        "street": "Praça da Sé",
        "neighborhood": "Centro",
        "city": "São Paulo",
        "state": "SP",
    }
    sanitize_cep.assert_called_once_with("01.001-000")


@pytest.mark.asyncio
@patch("app.services.geocoding_service.sanitize_cep")
async def test_fetch_address_from_cep_http_error(sanitize_cep, monkeypatch):
    sanitize_cep.return_value = "00000000"
    _mock_async_client(monkeypatch, raise_exc=httpx.HTTPError("boom"))

    with pytest.raises(geocoding_service.HTTPException) as excinfo:
        await geocoding_service.fetch_address_from_cep("00000-000")

    assert excinfo.value.status_code == geocoding_service.status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
@patch("app.services.geocoding_service.sanitize_cep")
async def test_fetch_address_from_cep_not_found(sanitize_cep, monkeypatch):
    sanitize_cep.return_value = "99999999"
    _mock_async_client(monkeypatch, response_json={"erro": True})

    with pytest.raises(geocoding_service.HTTPException) as excinfo:
        await geocoding_service.fetch_address_from_cep("99999-999")

    assert excinfo.value.status_code == geocoding_service.status.HTTP_400_BAD_REQUEST
    assert "CEP 99999-999 não encontrado" in excinfo.value.detail


@pytest.mark.asyncio
async def test_fetch_coordinates_requires_key(monkeypatch):
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "", raising=False)

    result = await geocoding_service.fetch_coordinates("Rua Sem Nome, 123")
    assert result is None


@pytest.mark.asyncio
async def test_fetch_coordinates_returns_values(monkeypatch):
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "abc", raising=False)
    payload = {
        "status": "OK",
        "results": [{"geometry": {"location": {"lat": 1.23, "lng": 4.56}}}],
    }
    _mock_async_client(monkeypatch, response_json=payload)

    result = await geocoding_service.fetch_coordinates("Av. Paulista, 1000")
    assert result == (1.23, 4.56)


@pytest.mark.asyncio
async def test_fetch_coordinates_handles_bad_status(monkeypatch):
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "abc", raising=False)
    payload = {"status": "ZERO_RESULTS", "results": []}
    _mock_async_client(monkeypatch, response_json=payload)

    assert await geocoding_service.fetch_coordinates("Deserto") is None


@pytest.mark.asyncio
async def test_fetch_coordinates_http_error(monkeypatch):
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "abc", raising=False)
    _mock_async_client(monkeypatch, get_exc=httpx.HTTPError("boom"))

    assert await geocoding_service.fetch_coordinates("Rua Inexistente") is None


@pytest.mark.asyncio
async def test_fetch_zip_code_requires_key(monkeypatch):
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "", raising=False)

    assert await geocoding_service.fetch_zip_code("Rua Sem Nome") is None


@pytest.mark.asyncio
async def test_fetch_zip_code_returns_digits(monkeypatch):
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "abc", raising=False)
    payload = {
        "status": "OK",
        "results": [
            {
                "address_components": [
                    {"types": ["postal_code"], "long_name": "13201-000"},
                ]
            }
        ],
    }
    _mock_async_client(monkeypatch, response_json=payload)

    assert await geocoding_service.fetch_zip_code("Rua do Teste") == "13201000"


@pytest.mark.asyncio
async def test_fetch_zip_code_without_postal_code(monkeypatch):
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "abc", raising=False)
    payload = {"status": "OK", "results": [{"address_components": [{"types": ["route"], "long_name": "Rua"}]}]}
    _mock_async_client(monkeypatch, response_json=payload)

    assert await geocoding_service.fetch_zip_code("Rua Sem CEP") is None


@pytest.mark.asyncio
async def test_fetch_zip_code_bad_status(monkeypatch):
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "abc", raising=False)
    _mock_async_client(monkeypatch, response_json={"status": "INVALID_REQUEST", "results": []})

    assert await geocoding_service.fetch_zip_code("Rua Errada") is None


@pytest.mark.asyncio
async def test_fetch_zip_code_http_error(monkeypatch):
    monkeypatch.setattr(geocoding_service.settings, "google_maps_api_key", "abc", raising=False)
    _mock_async_client(monkeypatch, get_exc=httpx.HTTPError("boom"))

    assert await geocoding_service.fetch_zip_code("Rua Fora") is None


def test_haversine_distance():
    distance = geocoding_service.haversine_distance(-23.5489, -46.6388, -22.9056, -43.2094)
    assert distance == pytest.approx(357.64, rel=1e-3)
