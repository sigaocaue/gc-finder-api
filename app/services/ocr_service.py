"""Serviço de OCR usando EasyOCR com padrão singleton."""

import asyncio
import logging
import time as time_module

import easyocr

logger = logging.getLogger(__name__)

# Singleton do reader EasyOCR
_reader: easyocr.Reader | None = None


def _get_reader() -> easyocr.Reader:
    """Retorna a instância singleton do EasyOCR Reader."""
    global _reader
    if _reader is None:
        logger.info("[ocr_service] Reader EasyOCR inicializado (primeira vez)")
        _reader = easyocr.Reader(["pt", "en"], gpu=False)
    return _reader


def _run_ocr(image_path: str) -> list[str]:
    """Executa OCR na imagem e retorna lista de textos detectados (síncrono)."""
    reader = _get_reader()
    start = time_module.monotonic()
    results = reader.readtext(image_path, detail=0)
    elapsed = round(time_module.monotonic() - start, 2)
    logger.info(
        "[ocr_service] OCR concluído: %d blocos em %ss (image=%s)",
        len(results),
        elapsed,
        image_path,
    )
    return results


async def extract_text(image_path: str) -> list[str]:
    """Executa OCR de forma assíncrona usando asyncio.to_thread."""
    return await asyncio.to_thread(_run_ocr, image_path)
