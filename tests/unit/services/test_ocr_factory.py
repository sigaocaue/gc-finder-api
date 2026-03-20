"""Testes unitários da factory de serviços OCR."""

from unittest.mock import patch

import pytest

from app.services.ocr.factory import (
    VALID_OCR_SERVICES,
    _normalize_name,
    get_available_services,
    get_ocr_service,
    validate_ocr_service,
)


class TestNormalizeName:
    """Testa a normalização de nomes de serviços OCR."""

    def test_lowercase(self):
        assert _normalize_name("EasyOCR") == "easyocr"

    def test_strips_whitespace(self):
        assert _normalize_name("  tesseract  ") == "tesseract"

    def test_replaces_spaces_with_underscore(self):
        assert _normalize_name("Google Document AI") == "google_document_ai"

    def test_replaces_hyphens_with_underscore(self):
        assert _normalize_name("google-documentai") == "google_documentai"


class TestGetAvailableServices:
    """Testa a leitura dos serviços disponíveis no ambiente."""

    @patch("app.services.ocr.factory.settings")
    def test_default_only_easyocr(self, mock_settings):
        mock_settings.ocr_available_services = "easyocr"
        result = get_available_services()
        assert result == {"easyocr"}

    @patch("app.services.ocr.factory.settings")
    def test_multiple_services(self, mock_settings):
        mock_settings.ocr_available_services = "easyocr,tesseract,google_documentai"
        result = get_available_services()
        assert result == {"easyocr", "tesseract", "google_documentai"}

    @patch("app.services.ocr.factory.settings")
    def test_case_insensitive(self, mock_settings):
        mock_settings.ocr_available_services = "EasyOCR, Tesseract"
        result = get_available_services()
        assert "easyocr" in result
        assert "tesseract" in result


class TestValidateOcrService:
    """Testa a validação do serviço OCR."""

    @patch("app.services.ocr.factory.settings")
    def test_valid_and_available(self, mock_settings):
        mock_settings.ocr_available_services = "easyocr"
        result = validate_ocr_service("EasyOCR")
        assert result == "easyocr"

    @patch("app.services.ocr.factory.settings")
    def test_invalid_service_raises(self, mock_settings):
        mock_settings.ocr_available_services = "easyocr"
        with pytest.raises(ValueError, match="não é válido"):
            validate_ocr_service("openai_vision")

    @patch("app.services.ocr.factory.settings")
    def test_valid_but_unavailable_raises(self, mock_settings):
        mock_settings.ocr_available_services = "easyocr"
        with pytest.raises(ValueError, match="não está disponível"):
            validate_ocr_service("tesseract")

    @patch("app.services.ocr.factory.settings")
    def test_case_insensitive_input(self, mock_settings):
        mock_settings.ocr_available_services = "tesseract"
        result = validate_ocr_service("TESSERACT")
        assert result == "tesseract"

    @patch("app.services.ocr.factory.settings")
    def test_google_documentai_valid(self, mock_settings):
        mock_settings.ocr_available_services = "google_documentai"
        result = validate_ocr_service("google_documentai")
        assert result == "google_documentai"


class TestGetOcrService:
    """Testa a criação de instâncias de serviços OCR."""

    def test_returns_easyocr_instance(self):
        from app.services.ocr.easyocr_service import EasyOcrService
        ocr = get_ocr_service("easyocr")
        assert isinstance(ocr, EasyOcrService)

    def test_returns_tesseract_instance(self):
        from app.services.ocr.tesseract_service import TesseractOcrService
        ocr = get_ocr_service("tesseract")
        assert isinstance(ocr, TesseractOcrService)

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError, match="não implementado"):
            get_ocr_service("inexistente")
