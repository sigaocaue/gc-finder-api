"""Classe base abstrata para serviços de OCR."""

from abc import ABC, abstractmethod


class OcrService(ABC):
    """Interface comum para todos os provedores de OCR."""

    @abstractmethod
    async def extract_text(self, image_path: str) -> list[str]:
        """Extrai textos de uma imagem e retorna lista de strings detectadas."""
        ...
