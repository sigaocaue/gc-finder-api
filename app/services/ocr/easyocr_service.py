"""Serviço de OCR usando EasyOCR com padrão singleton."""

import asyncio
import logging
import time as time_module

from app.services.ocr.base import OcrService

logger = logging.getLogger(__name__)

try:
    import easyocr

    _EASYOCR_AVAILABLE = True
except ImportError:
    _EASYOCR_AVAILABLE = False

# Singleton do reader EasyOCR
_reader = None


def is_available() -> bool:
    """Verifica se o EasyOCR está instalado."""
    return _EASYOCR_AVAILABLE


def _get_reader():
    """Retorna a instância singleton do EasyOCR Reader."""
    if not _EASYOCR_AVAILABLE:
        raise RuntimeError(
            "EasyOCR não está instalado. "
            "Instale com: poetry install --with ocr"
        )

    global _reader
    if _reader is None:
        logger.info("[ocr:easyocr] Reader inicializado (primeira vez)")
        _reader = easyocr.Reader(["pt", "en"], gpu=False)
    return _reader


def _run_ocr(image_path: str) -> list[str]:
    """Executa OCR na imagem e retorna lista de textos detectados (síncrono)."""
    reader = _get_reader()
    start = time_module.monotonic()
    results = reader.readtext(image_path, detail=0)
    elapsed = round(time_module.monotonic() - start, 2)
    logger.info(
        "[ocr:easyocr] OCR concluído: %d blocos em %ss (image=%s)",
        len(results),
        elapsed,
        image_path,
    )
    return results


class EasyOcrService(OcrService):
    """Implementação de OCR usando EasyOCR."""

    async def extract_text(self, image_path: str) -> list[str]:
        """Executa OCR de forma assíncrona usando asyncio.to_thread."""
        return await asyncio.to_thread(_run_ocr, image_path)
