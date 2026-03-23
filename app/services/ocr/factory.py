"""Factory para criação de serviços OCR com validação de disponibilidade."""

import logging

from app.config import settings
from app.services.ocr.base import OcrService

logger = logging.getLogger(__name__)

# Mapeamento canônico: chave normalizada → nome de exibição
VALID_OCR_SERVICES = {
    "tesseract": "Tesseract",
    "google_documentai": "Google Document AI",
}


def _normalize_name(name: str) -> str:
    """Normaliza o nome do serviço OCR para comparação case-insensitive."""
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def get_available_services() -> set[str]:
    """Retorna o conjunto de serviços OCR disponíveis no ambiente (normalizados)."""
    raw = settings.ocr_available_services
    return {_normalize_name(s) for s in raw.split(",") if s.strip()}


def validate_ocr_service(ocr_service: str) -> str:
    """Valida o nome do serviço OCR e retorna o nome normalizado.

    Raises:
        ValueError: Se o serviço não é válido ou não está disponível.
    """
    normalized = _normalize_name(ocr_service)

    if normalized not in VALID_OCR_SERVICES:
        valid_names = ", ".join(sorted(VALID_OCR_SERVICES.values()))
        raise ValueError(
            f"Serviço OCR '{ocr_service}' não é válido. "
            f"Opções disponíveis: {valid_names}."
        )

    available = get_available_services()
    if normalized not in available:
        available_names = ", ".join(
            VALID_OCR_SERVICES[k] for k in sorted(available) if k in VALID_OCR_SERVICES
        )
        raise ValueError(
            f"Serviço OCR '{VALID_OCR_SERVICES[normalized]}' não está disponível "
            f"neste ambiente. Serviços disponíveis: {available_names or 'nenhum'}."
        )

    return normalized


def get_ocr_service(ocr_service: str) -> OcrService:
    """Cria e retorna a instância do serviço OCR solicitado.

    O nome já deve ter sido validado com validate_ocr_service().
    """
    normalized = _normalize_name(ocr_service)

    if normalized == "tesseract":
        from app.services.ocr.tesseract_service import TesseractOcrService
        return TesseractOcrService()

    if normalized == "google_documentai":
        from app.services.ocr.google_documentai_service import GoogleDocumentAiService
        return GoogleDocumentAiService(
            project_id=settings.google_documentai_project_id,
            location=settings.google_documentai_location,
            processor_id=settings.google_documentai_processor_id,
            credentials_json=settings.google_cloud_credentials_json,
        )

    raise ValueError(f"Serviço OCR '{ocr_service}' não implementado.")
