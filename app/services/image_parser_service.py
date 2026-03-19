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


def _normalize_phone(raw: str) -> str:
    """Remove tudo que não é dígito do telefone."""
    return re.sub(r"\D", "", raw)


def _normalize_time(hour_str: str, minute_str: str) -> str:
    """Converte hora e minuto para formato HH:MM."""
    hour = int(hour_str)
    minute = int(minute_str) if minute_str else 0
    return f"{hour:02d}:{minute:02d}"


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
    """Analisa o texto extraído pelo OCR e retorna dados estruturados do GC."""
    full_text = "\n".join(lines)

    # --- Nome do GC ---
    name = None
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 4 and not _is_noise_line(stripped):
            # Ignora linhas que são claramente endereço
            if _ADDRESS_PATTERN.match(stripped):
                continue
            name = stripped
            break

    if not name:
        name = lines[0].strip() if lines else ""
        logger.warning("[image_parser] Campo não encontrado: name — usando primeira linha")

    # --- Logradouro e número ---
    street = None
    number = None
    address_match = _ADDRESS_PATTERN.search(full_text)
    if address_match:
        # Pega o trecho completo do endereço até vírgula ou fim de linha
        start = address_match.start()
        # Busca até o fim da linha ou próximo delimitador
        end_match = re.search(r"[,\n]", full_text[address_match.end():])
        if end_match:
            street_end = address_match.end() + end_match.start()
        else:
            street_end = address_match.end()
        street = full_text[start:street_end].strip()

        # Busca número após o endereço
        remaining = full_text[street_end:]
        num_match = _NUMBER_PATTERN.search(remaining[:30])
        if num_match:
            number = num_match.group(1)
        else:
            # Tenta buscar número na mesma linha
            full_address_line = full_text[start:street_end + 30]
            num_match = _NUMBER_PATTERN.search(full_address_line)
            if num_match:
                number = num_match.group(1)

    if not street:
        logger.warning("[image_parser] Campo não encontrado: street — campo obrigatório")
        street = ""

    if not number:
        logger.warning("[image_parser] Campo não encontrado: number")

    # --- Complemento ---
    complement = None
    for line in lines:
        if _COMPLEMENT_KEYWORDS.search(line):
            complement = line.strip()
            break

    # --- Bairro ---
    neighborhood = None
    neighborhood_match = _NEIGHBORHOOD_PATTERN.search(full_text)
    if neighborhood_match:
        neighborhood = neighborhood_match.group(0).strip()
    else:
        logger.warning("[image_parser] Campo não encontrado: neighborhood — usando valor padrão")

    # --- Cidade e Estado (padrões: Jundiaí, SP) ---
    city = "Jundiaí"
    state = "SP"

    # Tenta detectar cidade/estado no texto
    city_state_match = re.search(
        r"(\w[\w\s]+?)\s*[-–/]\s*(SP|RJ|MG|PR|SC|RS|BA|CE|PE|GO|DF|ES|MA|PA|PB|PI|RN|SE|AL|AM|AP|AC|MT|MS|RO|RR|TO)\b",
        full_text,
        re.IGNORECASE,
    )
    if city_state_match:
        city = city_state_match.group(1).strip()
        state = city_state_match.group(2).upper()

    # --- Dia da semana e horário (encontros) ---
    meetings: list[MeetingExtracted] = []
    weekday_matches = _WEEKDAY_PATTERN.finditer(full_text)
    for wm in weekday_matches:
        day_name = wm.group(1).lower()
        weekday = WEEKDAY_MAP.get(day_name)
        if weekday is None:
            continue

        # Procura horário próximo ao dia da semana
        nearby_text = full_text[wm.start():wm.start() + 80]
        time_match = _TIME_PATTERN.search(nearby_text)
        if time_match:
            start_time = _normalize_time(time_match.group(1), time_match.group(2))
            meetings.append(
                MeetingExtracted(weekday=weekday, start_time=start_time)
            )
        else:
            logger.warning(
                "[image_parser] Dia '%s' encontrado sem horário associado", day_name
            )

    if not meetings:
        logger.warning("[image_parser] Campo não encontrado: meetings")

    # --- Telefones (contatos dos líderes) ---
    phones = _PHONE_PATTERN.findall(full_text)
    normalized_phones = [_normalize_phone(p) for p in phones]

    # --- Monta líderes ---
    # Heurística: se existem telefones mas sem nomes de líderes identificáveis,
    # cria líderes genéricos; caso contrário tenta extrair nomes
    leaders: list[LeaderExtracted] = []

    # Tenta encontrar nomes de líderes: linhas curtas (nomes) próximas a telefones
    leader_names: list[str] = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Nome de líder: linha curta (2-40 chars), sem números longos, sem endereço
        if (
            2 < len(stripped) < 40
            and not _PHONE_PATTERN.search(stripped)
            and not _ADDRESS_PATTERN.search(stripped)
            and not _WEEKDAY_PATTERN.search(stripped)
            and not _TIME_PATTERN.search(stripped)
            and not _COMPLEMENT_KEYWORDS.search(stripped)
            and not _NEIGHBORHOOD_PATTERN.match(stripped)
            and stripped != name
            and not re.search(r"\d{3,}", stripped)
        ):
            # Verifica se a próxima ou anterior linha tem telefone
            context_start = max(0, i - 1)
            context_end = min(len(lines), i + 3)
            context_lines = lines[context_start:context_end]
            context_text = " ".join(context_lines)
            if _PHONE_PATTERN.search(context_text):
                leader_names.append(stripped)

    if leader_names:
        # Distribui telefones entre líderes
        phones_per_leader = max(1, len(normalized_phones) // len(leader_names))
        for idx, leader_name in enumerate(leader_names):
            start_idx = idx * phones_per_leader
            end_idx = start_idx + phones_per_leader if idx < len(leader_names) - 1 else len(normalized_phones)
            contacts = [
                LeaderContactExtracted(type="whatsapp", value=p)
                for p in normalized_phones[start_idx:end_idx]
            ]
            leaders.append(LeaderExtracted(name=leader_name, contacts=contacts))
    elif normalized_phones:
        # Sem nomes identificáveis: cada telefone vira um líder sem nome definido
        for phone in normalized_phones:
            leaders.append(
                LeaderExtracted(
                    name="Líder",
                    contacts=[LeaderContactExtracted(type="whatsapp", value=phone)],
                )
            )

    if not leaders:
        logger.warning("[image_parser] Campo não encontrado: leaders")

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
    )
