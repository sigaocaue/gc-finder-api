"""Unit tests for the GC image import router."""

import asyncio
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.routers.gc_image_import import (
    _normalize_url_list,
    save_imported_gc,
    start_image_import,
    stream_job_status,
)
from app.schemas.gc_image_import import GcImportSaveRequest


class DummyUpload:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


def make_form(images=None, images_urls=None, ocr_service="easyocr"):
    return SimpleNamespace(
        images=images,
        images_urls=images_urls,
        ocr_service=SimpleNamespace(value=ocr_service),
    )


@pytest.mark.asyncio
async def test_start_image_import_requires_input(monkeypatch):
    form = make_form(images=None, images_urls=None)
    user = SimpleNamespace(id="u", email="e")

    with pytest.raises(HTTPException) as excinfo:
        await start_image_import(user, form)

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_start_image_import_validates_ocr(monkeypatch):
    form = make_form(images=None, images_urls=["http://example.com/image.jpg"], ocr_service="easyocr")
    user = SimpleNamespace(id="u", email="e")
    monkeypatch.setattr(
        "app.routers.gc_image_import.validate_ocr_service",
        MagicMock(side_effect=ValueError("OCR offline")),
    )

    with pytest.raises(HTTPException) as excinfo:
        await start_image_import(user, form)

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_start_image_import_file_success(monkeypatch, tmp_path):
    upload = DummyUpload("photo.jpg", b"123")
    form = make_form(images=[upload], images_urls=None, ocr_service="easyocr")
    user = SimpleNamespace(id="u", email="e")

    start_job = AsyncMock(return_value="job-123")
    process_image_job = AsyncMock()

    monkeypatch.setattr("app.routers.gc_image_import.tempfile.gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr("app.routers.gc_image_import.validate_ocr_service", lambda value: value)
    monkeypatch.setattr("app.routers.gc_image_import.start_job", start_job)
    monkeypatch.setattr("app.routers.gc_image_import.process_image_job", process_image_job)

    response = await start_image_import(user, form)

    assert response.data.job_id == "job-123"
    start_job.assert_awaited_once()

    files = list(tmp_path.iterdir())
    for file in files:
        file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_start_image_import_invalid_extension(monkeypatch, tmp_path):
    upload = DummyUpload("photo.txt", b"123")
    form = make_form(images=[upload], images_urls=None, ocr_service="easyocr")
    user = SimpleNamespace(id="u", email="e")
    monkeypatch.setattr("app.routers.gc_image_import.tempfile.gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr("app.routers.gc_image_import.validate_ocr_service", lambda value: value)

    with pytest.raises(HTTPException) as excinfo:
        await start_image_import(user, form)

    assert "Extensão '.txt'" in excinfo.value.detail[0]


@pytest.mark.asyncio
async def test_start_image_import_invalid_url(monkeypatch):
    form = make_form(images=None, images_urls=["ftp://invalid"], ocr_service="easyocr")
    user = SimpleNamespace(id="u", email="e")
    monkeypatch.setattr("app.routers.gc_image_import.validate_ocr_service", lambda value: value)

    with pytest.raises(HTTPException) as excinfo:
        await start_image_import(user, form)

    assert "não é uma URL válida" in excinfo.value.detail[0]


@pytest.mark.asyncio
async def test_start_image_import_url_job(monkeypatch, tmp_path):
    form = make_form(images=None, images_urls=['["http://a","https://b"]'], ocr_service="easyocr")
    user = SimpleNamespace(id="u", email="e")
    monkeypatch.setattr("app.routers.gc_image_import.validate_ocr_service", lambda value: value)

    start_job = AsyncMock(return_value="job-789")
    monkeypatch.setattr("app.routers.gc_image_import.start_job", start_job)
    monkeypatch.setattr("app.routers.gc_image_import.process_image_job", AsyncMock())

    response = await start_image_import(user, form)

    assert response.data.job_id == "job-789"
    start_job.assert_awaited_once()
    assert start_job.call_args[0][1] == ["http://a", "https://b"]


def test_normalize_url_list_variants():
    assert _normalize_url_list([]) == []
    assert _normalize_url_list(["   "]) == ["   "]
    assert _normalize_url_list(['["a","b"]']) == ["a", "b"]
    assert _normalize_url_list(["http://a,http://b"]) == ["http://a", "http://b"]
    assert _normalize_url_list(["invalid[", "http://ok"]) == ["invalid[", "http://ok"]


@pytest.mark.asyncio
async def test_stream_job_status_missing(monkeypatch):
    monkeypatch.setattr("app.routers.gc_image_import.get_job_state", AsyncMock(return_value=None))

    with pytest.raises(Exception) as excinfo:
        await stream_job_status("job", SimpleNamespace(id="u", email="e"))

    assert excinfo.value.status_code == 404


@pytest.mark.asyncio
async def test_stream_job_status_generates_events(monkeypatch):
    pending = {"status": "processing", "progress": "half"}
    done = {
        "status": "done",
        "result": [
            {"name": "GC", "street": "Rua", "city": "Cidade", "state": "ST"}
        ],
    }
    state_sequence = [pending.copy(), pending.copy(), done.copy()]
    get_state = AsyncMock(side_effect=state_sequence.copy())
    monkeypatch.setattr("app.routers.gc_image_import.get_job_state", get_state)
    monkeypatch.setattr("app.routers.gc_image_import.asyncio.sleep", AsyncMock())

    response = await stream_job_status("job", SimpleNamespace(id="u", email="e"))
    events = []
    async for chunk in response.body_iterator:
        events.append(chunk)

    assert any("processing" in chunk for chunk in events)
    assert any("done" in chunk for chunk in events)


@pytest.mark.asyncio
@patch("app.routers.gc_image_import.GcImageSaveService")
async def test_save_imported_gc_success(mock_service):
    service = mock_service.return_value
    gc = SimpleNamespace(
        id=uuid.uuid4(),
        name="GC Salvo",
        zip_code="00000-000",
        street="Rua X",
        number="1",
        complement=None,
        neighborhood="Centro",
        city="Cidade",
        state="ST",
        latitude=0.0,
        longitude=0.0,
        is_active=True,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-02T00:00:00",
        description=None,
        meetings=[],
        leaders=[],
        medias=[],
    )
    service.save = AsyncMock(return_value=gc)

    body = GcImportSaveRequest(
        name="GC",
        street="Rua X",
        city="Cidade",
        state="ST",
    )

    response = await save_imported_gc(body, current_user=SimpleNamespace(id="u", email="e"), db=SimpleNamespace())

    assert response.message == "GC cadastrado com sucesso."
    service.save.assert_awaited_once_with(body)


@pytest.mark.asyncio
async def test_save_imported_gc_requires_name():
    body = GcImportSaveRequest(
        name="",
        street="Rua",
        city="C",
        state="ST",
    )

    with pytest.raises(HTTPException) as excinfo:
        await save_imported_gc(body, current_user=SimpleNamespace(id="u", email="e"), db=SimpleNamespace())

    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_save_imported_gc_requires_street():
    body = GcImportSaveRequest(
        name="GC",
        street="",
        city="C",
        state="ST",
    )

    with pytest.raises(Exception) as excinfo:
        await save_imported_gc(body, current_user=SimpleNamespace(id="u", email="e"), db=SimpleNamespace())

    assert excinfo.value.status_code == 400
