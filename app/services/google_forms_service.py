"""Serviço de envio de formulário de interesse via Google Forms."""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def submit_interest(
    name: str,
    email: str,
    phone: str,
    zip_code: str,
    message: str,
) -> bool:
    """Envia os dados de interesse para o Google Forms via POST.

    Retorna True se o envio for bem-sucedido, False em caso de falha.
    Não levanta exceção — apenas loga o erro.
    """
    if not settings.google_forms_submit_url:
        logger.warning("URL do Google Forms não configurada; envio ignorado")
        return False

    # Mapeamento dos campos do formulário (entry IDs do Google Forms)
    form_data = {
        "entry.1": name,
        "entry.2": email,
        "entry.3": phone,
        "entry.4": zip_code,
        "entry.5": message,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.post(
                settings.google_forms_submit_url,
                data=form_data,
            )
            # Google Forms retorna 200 mesmo para formResponse
            if response.status_code in (200, 302):
                logger.info("Formulário de interesse enviado com sucesso para %s", email)
                return True

            logger.warning(
                "Resposta inesperada do Google Forms: status=%d",
                response.status_code,
            )
            return False

        except httpx.HTTPError as exc:
            logger.error("Erro ao enviar formulário de interesse: %s", exc)
            return False
