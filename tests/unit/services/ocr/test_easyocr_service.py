"""Unit tests covering the EasyOCR wrapper."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ocr import easyocr_service


@pytest.fixture(autouse=True)
def reset_singleton():
    original_reader = easyocr_service._reader
    yield
    easyocr_service._reader = original_reader


def test_is_available_flag(monkeypatch):
    monkeypatch.setattr(easyocr_service, "_EASYOCR_AVAILABLE", False)
    assert easyocr_service.is_available() is False
    monkeypatch.setattr(easyocr_service, "_EASYOCR_AVAILABLE", True)
    assert easyocr_service.is_available() is True


def test_get_reader_requires_install(monkeypatch):
    monkeypatch.setattr(easyocr_service, "_EASYOCR_AVAILABLE", False)

    with pytest.raises(RuntimeError):
        easyocr_service._get_reader()


def test_get_reader_returns_singleton(monkeypatch):
    mock_reader = MagicMock()
    monkeypatch.setattr(easyocr_service, "_EASYOCR_AVAILABLE", True)
    mock_easyocr = MagicMock()
    mock_easyocr.Reader.return_value = mock_reader
    monkeypatch.setattr(easyocr_service, "easyocr", mock_easyocr, raising=False)
    easyocr_service._reader = None

    first = easyocr_service._get_reader()
    second = easyocr_service._get_reader()

    assert first is mock_reader
    assert second is mock_reader


def test_run_ocr_logs_and_returns(monkeypatch):
    reader = MagicMock()
    reader.readtext.return_value = ["resultado"]
    monkeypatch.setattr(easyocr_service, "_get_reader", lambda: reader)
    # control time progression
    times = [1.0, 2.5]

    def fake_monotonic():
        return times.pop(0)

    monkeypatch.setattr(easyocr_service.time_module, "monotonic", fake_monotonic)

    result = easyocr_service._run_ocr("img.png")

    reader.readtext.assert_called_once_with("img.png", detail=0)
    assert result == ["resultado"]


@pytest.mark.asyncio
@patch("app.services.ocr.easyocr_service._run_ocr", autospec=True)
async def test_extract_text_invokes_thread(mock_run):
    mock_run.return_value = ["texto"]
    monkeypatched = AsyncMock()
    monkeypatched.return_value = ["texto"]
    asyncio_to_thread = AsyncMock(return_value=["texto"])

    with patch("app.services.ocr.easyocr_service.asyncio.to_thread", asyncio_to_thread):
        service = easyocr_service.EasyOcrService()
        result = await service.extract_text("path.png")

    asyncio_to_thread.assert_awaited_once_with(easyocr_service._run_ocr, "path.png")
    assert result == ["texto"]
