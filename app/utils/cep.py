"""Utilitários para manipulação e validação de CEP."""

import re


def sanitize_cep(cep: str) -> str:
    """Remove todos os caracteres não numéricos do CEP."""
    return re.sub(r"\D", "", cep)


def format_cep(cep: str) -> str:
    """Formata o CEP no padrão 00000-000."""
    digits = sanitize_cep(cep)
    if len(digits) != 8:
        return digits
    return f"{digits[:5]}-{digits[5:]}"


def is_valid_cep(cep: str) -> bool:
    """Verifica se o CEP possui exatamente 8 dígitos após sanitização."""
    digits = sanitize_cep(cep)
    return len(digits) == 8 and digits.isdigit()
