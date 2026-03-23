"""Parser de regex para extrair dados estruturados do texto bruto do OCR."""

import logging
import re

from app.schemas.gc_image_import import (
    GcExtractedData,
    LeaderContactExtracted,
    LeaderExtracted,
    MeetingExtracted,
)

logger = logging.getLogger(__name__)

WEEKDAY_MAP = {
    "domingo": 0,
    "segunda": 1,
    "terca": 2,
    "terça": 2,
    "quarta": 3,
    "quinta": 4,
    "sexta": 5,
    "sabado": 6,
    "sábado": 6,
}

# Padrões de regex
_ADDRESS_PATTERN = re.compile(
    r"(rua|avenida|av\.?|alameda|travessa|estrada|rodovia)\s+[^,\n]+",
    re.IGNORECASE,
)
_NUMBER_PATTERN = re.compile(
    r"(?:,\s*|n[°ºo.]?\s*)(\d+)",
    re.IGNORECASE,
)
_COMPLEMENT_KEYWORDS = re.compile(
    r"\b(casa|apto|apartamento|bloco|cond\.?|condomínio|condominio|torre)\b",
    re.IGNORECASE,
)
_NEIGHBORHOOD_PATTERN = re.compile(
    r"\b(jardim|jd\.?|vila|vl\.?|bairro|parque|pq\.?|residencial|res\.?)\s+\w[\w\s]*",
    re.IGNORECASE,
)
_WEEKDAY_PATTERN = re.compile(
    r"(segunda|terça|terca|quarta|quinta|sexta|sábado|sabado|domingo)",
    re.IGNORECASE,
)
_TIME_PATTERN = re.compile(r"(\d{1,2})[h:](\d{0,2})")
_PHONE_PATTERN = re.compile(r"\(?\d{2}\)?\s?\d{4,5}[-\s]?\d{4}")
OCR_CORRECTIONS = {
    "|": "",
    ";": "",
}


def _normalize_phone(raw: str) -> str:
    """Remove tudo que não é dígito do telefone."""
    return re.sub(r"\D", "", raw)


def _normalize_time(time_str: str) -> str | None:
    """Converte horário para formato HH:MM."""

    # Substitui padrões específicos primeiro
    # "2OH" ou "20H" deve virar "20"
    time_str = time_str.replace("O", "0")
    time_str = time_str.replace("OH", "0h")

    # Remove caracteres não numéricos
    cleaned = re.sub(r"\D", "", time_str)

    if not cleaned:
        return None

    # Se tem 2 dígitos, pode ser 20 (20h) ou 02 (2h)
    # Precisamos verificar o contexto
    if len(cleaned) <= 2:
        hour = int(cleaned)
        return f"{hour:02d}:00"

    # Caso "2030" -> "20:30"
    if len(cleaned) == 4:
        return f"{cleaned[:2]}:{cleaned[2:]}"

    return None


def _extract_weekday_and_time(text: str) -> tuple[int | None, str | None]:
    """Extrai dia da semana e horário de um texto."""
    text_lower = text.lower()

    # Encontra dia da semana
    weekday = None
    for day_name, day_num in WEEKDAY_MAP.items():
        if day_name in text_lower:
            weekday = day_num
            break

    # Encontra horário
    time_str = None
    # Normaliza o texto para substituir O por 0
    normalized_text = text.replace("O", "0").replace("OH", "0h")
    # Procura padrões como "20h", "20:00", "20H", "20"
    time_match = re.search(r"(\d{1,2})[hH:0](\d{0,2})", normalized_text)
    if time_match:
        hour = int(time_match.group(1))
        # Se hour for 2 e o texto original tinha "O" ou "OH", provavelmente é 20
        if hour == 2 and ("O" in text or "OH" in text):
            hour = 20
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        time_str = f"{hour:02d}:{minute:02d}"

    return weekday, time_str


def _extract_leader_name_and_phone(text: str) -> tuple[str | None, str | None]:
    """Extrai nome e telefone de uma linha."""
    phone_match = re.search(r"(\d{2,3})[.\s-]?(\d{4,5})[.\s-]?(\d{4})", text)
    if not phone_match:
        return None, None

    phone = f"{phone_match.group(1)}{phone_match.group(2)}{phone_match.group(3)}"

    # Nome é o que vem antes do telefone
    name = text[:phone_match.start()].strip()

    # Remove caracteres especiais do nome
    name = re.sub(r"[;:,|]", "", name).strip()

    return name if name else None, phone


def _correct_ocr_text(text: str) -> str:
    """Aplica correções conhecidas de OCR."""
    result = text
    for error, correction in OCR_CORRECTIONS.items():
        result = result.replace(error, correction)
    return result.strip()


def _is_noise_line(line: str) -> bool:
    """Verifica se a linha é ruído (dia, horário, telefone, ou muito curta)."""
    stripped = line.strip()
    if len(stripped) <= 4:
        return True
    if _WEEKDAY_PATTERN.search(stripped):
        return True
    if _TIME_PATTERN.search(stripped) and len(stripped) < 15:
        return True
    if _PHONE_PATTERN.search(stripped) and len(stripped) < 20:
        return True
    return False


def parse_ocr_text(lines: list[str]) -> GcExtractedData:
    """
    Analisa o texto extraído pelo OCR baseado na posição dos elementos.
    O layout é consistente:
        0: 'gc' (marcador)
        1: Nome do GC (parte 1)
        2: Nome do GC (parte 2, opcional) ou dia/horário
        3: Dia/horário (se parte 2 existe)
        4+: Líderes (nome + telefone)
        ...: Endereço (múltiplas linhas)
        -1: Rodapé (Lagoinha Jundiaí)
    """

    if not lines or lines[0].lower() != 'gc':
        logger.warning("[image_parser] Formato inválido: primeiro elemento não é 'gc'")
        return GcExtractedData(
            name="",
            street="",
            leaders=[],
            meetings=[],
        )

    # Remove elementos vazios e aplica correções
    corrected_lines = [_correct_ocr_text(line) for line in lines if line.strip()]

    idx = 1
    total = len(corrected_lines)

    # ========== 1. Nome do GC ==========
    name_parts = []

    if idx < total:
        name_parts.append(corrected_lines[idx])
        idx += 1

    # Verifica se o próximo elemento parece parte do nome (não contém dia/horário)
    if idx < total:
        next_line = corrected_lines[idx].lower()
        has_weekday = any(day in next_line for day in WEEKDAY_MAP.keys())
        # Normaliza horário para detectar padrões como "20h" ou "2OH"
        normalized = next_line.replace("O", "0")
        has_hour = 'h' in normalized and any(c.isdigit() for c in normalized)

        if not has_weekday and not has_hour:
            name_parts.append(corrected_lines[idx])
            idx += 1

    name = " ".join(name_parts)

    # ========== 2. Dia e Horário ==========
    meetings = []

    if idx < total:
        line = corrected_lines[idx]
        weekday, time_str = _extract_weekday_and_time(line)

        # Se não encontrou na primeira tentativa, tenta a próxima linha
        if weekday is None and time_str is None:
            idx += 1
            if idx < total:
                weekday, time_str = _extract_weekday_and_time(corrected_lines[idx])

        if weekday is not None and time_str is not None:
            meetings.append(MeetingExtracted(weekday=weekday, start_time=time_str))
        elif time_str:
            # Só tem horário, assume sexta como padrão
            meetings.append(MeetingExtracted(weekday=5, start_time=time_str))
            logger.warning("[image_parser] Horário encontrado sem dia da semana")

        idx += 1

    # ========== 3. Líderes ==========
    leaders = []

    while idx < total - 1:  # -1 para ignorar o rodapé
        line = corrected_lines[idx]
        name_leader, phone = _extract_leader_name_and_phone(line)

        if phone:
            # É uma linha de líder
            leader_name = name_leader if name_leader else "Líder"
            leaders.append(
                LeaderExtracted(
                    name=leader_name,
                    contacts=[LeaderContactExtracted(type="whatsapp", value=phone)],
                )
            )
            idx += 1
        else:
            # Pode ser parte do endereço
            break

    # ========== 4. Endereço ==========
    address_parts = []
    while idx < total - 1:  # -1 para ignorar o rodapé
        address_parts.append(corrected_lines[idx])
        idx += 1

    # Processa o endereço
    street = ""
    number = None
    complement = None
    neighborhood = None

    if address_parts:
        # Tenta identificar logradouro (começa com Rua, Avenida, etc)
        for i, part in enumerate(address_parts):
            part_lower = part.lower()
            if any(part_lower.startswith(prefix) for prefix in
                   ["rua", "avenida", "av", "alameda", "travessa", "estrada", "rodovia"]):
                street = part
                # Próximo pode ser número
                if i + 1 < len(address_parts):
                    next_part = address_parts[i + 1]
                    if next_part.isdigit():
                        number = next_part
                        # O resto pode ser complemento e bairro
                        if i + 2 < len(address_parts):
                            remaining = address_parts[i + 2:]
                            # Tenta identificar complemento
                            for rem in remaining:
                                rem_lower = rem.lower()
                                if any(keyword in rem_lower for keyword in ["casa", "apto", "bloco", "cond", "torre"]):
                                    complement = rem
                                    break
                            # O último antes do rodapé geralmente é o bairro
                            if not neighborhood and remaining:
                                neighborhood = remaining[-1] if remaining else None
                break

        # Se não encontrou logradouro específico, junta tudo
        if not street and address_parts:
            # Tenta encontrar número no meio do endereço
            full_address = " ".join(address_parts)
            # Busca padrão de rua + número
            addr_match = re.search(r"(Rua|Avenida|Av)\s+([^,\d]+)[,\s]*(\d+)", full_address, re.IGNORECASE)
            if addr_match:
                street = f"{addr_match.group(1)} {addr_match.group(2)}".strip()
                number = addr_match.group(3)
            else:
                street = full_address

    # ========== 5. Cidade ==========
    city = "Jundiaí"
    state = "SP"

    # Verifica se tem cidade diferente no texto
    full_text = " ".join(corrected_lines)
    if "itupeva" in full_text.lower():
        city = "Itupeva"

    logger.info(
        "[image_parser] Extraído — name=%s, street=%s, leaders=%d, meetings=%d",
        name,
        street,
        len(leaders),
        len(meetings),
    )

    return GcExtractedData(
        name=name,
        street=street,
        number=number,
        complement=complement,
        neighborhood=neighborhood,
        city=city,
        state=state,
        leaders=leaders,
        meetings=meetings,
        description=None,
        zip_code=None,
        latitude=None,
        longitude=None,
    )


if __name__ == "__main__":
    import json
    ocr1 = ['gc', 'Casais', 'Jardim Samambaias', 'Sexta-Feira | 2OH', 'Vanessa 1198331-2401', 'Cadu 1198331-2572',
            'Rua Carmela Nano', '432', 'Jardim das Samambalas', 'LA G01nA A Jund|A']
    resultado1 = parse_ocr_text(ocr1)
    resultado1 = json.dumps(resultado1.model_dump(), indent=2)
    print(resultado1)
