"""Pacote de serviços OCR — abstração para múltiplos provedores."""

from app.services.ocr.base import OcrService
from app.services.ocr.factory import get_ocr_service, validate_ocr_service

__all__ = ["OcrService", "get_ocr_service", "validate_ocr_service"]
