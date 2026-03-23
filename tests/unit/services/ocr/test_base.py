"""Tests for the OCR base interface."""

import pytest

from app.services.ocr.base import OcrService


class DummyService(OcrService):
    async def extract_text(self, image_path: str) -> list[str]:
        return [image_path]


def test_cannot_instantiate_abstract_class():
    with pytest.raises(TypeError):
        OcrService()


@pytest.mark.asyncio
async def test_subclasses_must_implement_extract_text():
    service = DummyService()
    result = await service.extract_text("path.jpg")
    assert result == ["path.jpg"]
