"""Serviço de OCR usando Google Document AI."""

import logging
import time as time_module

from app.services.ocr.base import OcrService

logger = logging.getLogger(__name__)

try:
    from google.cloud import documentai_v1 as documentai

    _DOCUMENTAI_AVAILABLE = True
except ImportError:
    _DOCUMENTAI_AVAILABLE = False


def is_available() -> bool:
    """Verifica se a biblioteca do Google Document AI está instalada."""
    return _DOCUMENTAI_AVAILABLE


class GoogleDocumentAiService(OcrService):
    """Implementação de OCR usando Google Document AI."""

    def __init__(self, project_id: str, location: str, processor_id: str):
        if not _DOCUMENTAI_AVAILABLE:
            raise RuntimeError(
                "google-cloud-documentai não está instalado. "
                "Instale com: poetry add google-cloud-documentai"
            )
        self._project_id = project_id
        self._location = location
        self._processor_id = processor_id
        self._client = documentai.DocumentProcessorServiceClient()
        self._resource_name = self._client.processor_path(
            project_id, location, processor_id
        )

    async def extract_text(self, image_path: str) -> list[str]:
        """Envia a imagem para o Document AI e retorna lista de textos."""
        import asyncio

        return await asyncio.to_thread(self._run_ocr, image_path)

    def _run_ocr(self, image_path: str) -> list[str]:
        """Executa OCR via Document AI (síncrono)."""
        start = time_module.monotonic()

        with open(image_path, "rb") as f:
            image_content = f.read()

        # Detecta o mime type pela extensão
        mime_type = "image/jpeg"
        if image_path.lower().endswith(".png"):
            mime_type = "image/png"

        raw_document = documentai.RawDocument(
            content=image_content,
            mime_type=mime_type,
        )
        request = documentai.ProcessRequest(
            name=self._resource_name,
            raw_document=raw_document,
        )

        result = self._client.process_document(request=request)
        document = result.document

        # Extrai linhas de texto do documento processado
        lines = [
            line.strip()
            for line in document.text.splitlines()
            if line.strip()
        ]

        elapsed = round(time_module.monotonic() - start, 2)
        logger.info(
            "[ocr:google_documentai] OCR concluído: %d linhas em %ss (image=%s)",
            len(lines),
            elapsed,
            image_path,
        )
        return lines
