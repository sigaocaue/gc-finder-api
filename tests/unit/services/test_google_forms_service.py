"""Unit tests for the Google Forms submission helper."""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from app.services import google_forms_service


def _patch_async_client(monkeypatch, *, status_code=200, raise_exc=None):
    response = MagicMock(status_code=status_code)
    response.raise_for_status = MagicMock()
    client = AsyncMock()
    if raise_exc:
        client.post.side_effect = raise_exc
    else:
        client.post.return_value = response

    ctx = AsyncMock()
    ctx.__aenter__.return_value = client
    ctx.__aexit__.return_value = False
    monkeypatch.setattr(
        google_forms_service.httpx, "AsyncClient", MagicMock(return_value=ctx)
    )
    return response


@pytest.mark.asyncio
async def test_submit_interest_requires_url(monkeypatch):
    monkeypatch.setattr(
        google_forms_service.settings,
        "google_forms_submit_url",
        "",
        raising=False,
    )

    assert await google_forms_service.submit_interest(
        "Nome", "email@example.com", "99999-999", "13201-000", "Olá"
    ) is False


@pytest.mark.asyncio
async def test_submit_interest_success(monkeypatch):
    monkeypatch.setattr(
        google_forms_service.settings,
        "google_forms_submit_url",
        "https://forms.example.com",
        raising=False,
    )
    response = _patch_async_client(monkeypatch, status_code=200)

    result = await google_forms_service.submit_interest(
        "Nome", "email@example.com", "99999-999", "13201-000", "Olá"
    )

    assert result is True
    response.raise_for_status.assert_not_called()
    google_forms_service.httpx.AsyncClient.assert_called_once()


@pytest.mark.asyncio
async def test_submit_interest_redirect_success(monkeypatch):
    monkeypatch.setattr(
        google_forms_service.settings,
        "google_forms_submit_url",
        "https://forms.example.com",
        raising=False,
    )
    _patch_async_client(monkeypatch, status_code=302)

    assert await google_forms_service.submit_interest(
        "Nome", "email@example.com", "99999-999", "13201-000", "Olá"
    ) is True


@pytest.mark.asyncio
async def test_submit_interest_non_ok_status(monkeypatch):
    monkeypatch.setattr(
        google_forms_service.settings,
        "google_forms_submit_url",
        "https://forms.example.com",
        raising=False,
    )
    _patch_async_client(monkeypatch, status_code=500)

    assert await google_forms_service.submit_interest(
        "Nome", "email@example.com", "99999-999", "13201-000", "Olá"
    ) is False


@pytest.mark.asyncio
async def test_submit_interest_http_error(monkeypatch):
    monkeypatch.setattr(
        google_forms_service.settings,
        "google_forms_submit_url",
        "https://forms.example.com",
        raising=False,
    )
    _patch_async_client(monkeypatch, raise_exc=httpx.HTTPError("boom"))

    assert await google_forms_service.submit_interest(
        "Nome", "email@example.com", "99999-999", "13201-000", "Olá"
    ) is False
