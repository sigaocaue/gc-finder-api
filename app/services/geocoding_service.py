"""Serviço de geocodificação: consulta CEP, coordenadas e cálculo de distância."""

import logging
import math

import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.utils.cep import sanitize_cep

logger = logging.getLogger(__name__)


async def fetch_address_from_cep(cep: str) -> dict:
    """Consulta a API ViaCEP para obter dados de endereço a partir do CEP.

    Retorna um dicionário com street, neighborhood, city e state.
    Levanta HTTPException 400 se o CEP for inválido ou não encontrado.
    """
    digits = sanitize_cep(cep)
    url = f"https://viacep.com.br/ws/{digits}/json/"

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.error("Erro ao consultar ViaCEP para o CEP %s: %s", cep, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Não foi possível consultar o CEP {cep}",
            )

    data = response.json()

    # A API ViaCEP retorna {"erro": true} quando o CEP não existe
    if data.get("erro"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"CEP {cep} não encontrado",
        )

    return {
        "street": data.get("logradouro", ""),
        "neighborhood": data.get("bairro", ""),
        "city": data.get("localidade", ""),
        "state": data.get("uf", ""),
    }


async def fetch_coordinates(address: str) -> tuple[float, float] | None:
    """Consulta a API do Google Maps Geocoding para obter latitude e longitude.

    Retorna uma tupla (lat, lng) ou None em caso de falha.
    Não levanta exceção — apenas loga o erro.
    """
    if not settings.google_maps_api_key:
        logger.warning("Google Maps API key não configurada; coordenadas não serão obtidas")
        return None

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "key": settings.google_maps_api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("status") != "OK" or not data.get("results"):
                logger.warning(
                    "Geocodificação sem resultados para '%s': status=%s",
                    address,
                    data.get("status"),
                )
                return None

            location = data["results"][0]["geometry"]["location"]
            return (location["lat"], location["lng"])

        except httpx.HTTPError as exc:
            logger.error("Erro ao geocodificar endereço '%s': %s", address, exc)
            return None


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calcula a distância em quilômetros entre dois pontos usando a fórmula de Haversine."""
    R = 6371.0  # Raio da Terra em km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c
