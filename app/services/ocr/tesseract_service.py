"""Serviço de OCR usando Tesseract via pytesseract."""

import asyncio
import logging
import time as time_module

from app.services.ocr.base import OcrService

logger = logging.getLogger(__name__)

try:
    import pytesseract
    from PIL import Image

    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False


def is_available() -> bool:
    """Verifica se o pytesseract e Pillow estão instalados."""
    return _TESSERACT_AVAILABLE


def _run_ocr(image_path: str) -> list[str]:
    """Executa OCR com Tesseract e retorna lista de textos detectados (síncrono)."""
    if not _TESSERACT_AVAILABLE:
        raise RuntimeError(
            "pytesseract não está instalado. "
            "Instale com: poetry add pytesseract Pillow"
        )

    start = time_module.monotonic()
    image = Image.open(image_path)
    # Usa português e inglês
    raw_text = pytesseract.image_to_string(image, lang="por+eng")
    elapsed = round(time_module.monotonic() - start, 2)

    # Divide o texto em linhas e remove linhas vazias
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    logger.info(
        "[ocr:tesseract] OCR concluído: %d linhas em %ss (image=%s)",
        len(lines),
        elapsed,
        image_path,
    )
    return lines


class TesseractOcrService(OcrService):
    """Implementação de OCR usando Tesseract."""

    async def extract_text(self, image_path: str) -> list[str]:
        """Executa OCR de forma assíncrona usando asyncio.to_thread."""
        return await asyncio.to_thread(_run_ocr, image_path)
