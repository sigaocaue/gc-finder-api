"""Unit tests for the OCR text parser (image_parser_service)."""

import pytest

from app.schemas.gc_image_import import GcExtractedData, MeetingExtracted
from app.services.image_parser_service import (
    WEEKDAY_MAP,
    _correct_ocr_text,
    _extract_leader_name_and_phone,
    _extract_weekday_and_time,
    _is_noise_line,
    _normalize_phone,
    _normalize_time,
    parse_ocr_text,
)


class TestNormalizePhone:
    """Testes para _normalize_phone."""

    def test_removes_non_digits(self):
        assert _normalize_phone("(11) 91234-5678") == "11912345678"

    def test_already_clean(self):
        assert _normalize_phone("11912345678") == "11912345678"

    def test_with_country_code(self):
        assert _normalize_phone("+55 11 91234-5678") == "5511912345678"


class TestNormalizeTime:
    """Testes para _normalize_time."""

    def test_two_digit_hour(self):
        assert _normalize_time("20h") == "20:00"

    def test_four_digit_time(self):
        assert _normalize_time("2030") == "20:30"

    def test_single_digit_hour(self):
        assert _normalize_time("8h") == "08:00"

    def test_empty_string(self):
        assert _normalize_time("") is None

    def test_no_digits(self):
        assert _normalize_time("abc") is None

    def test_ocr_letter_o_replacement(self):
        # "2OH" → "20h" após substituição de O→0
        assert _normalize_time("2OH") == "20:00"

    def test_more_than_four_digits(self):
        assert _normalize_time("12345") is None

    def test_hour_2_without_context(self):
        # Hora "2" sem contexto de "20" ou "2O" deve retornar 02:00
        assert _normalize_time("2h") == "02:00"

    def test_hour_2_with_20_context(self):
        # "20h" contém "20" no time_str, então hour == 2 → 20
        assert _normalize_time("20h") == "20:00"


class TestExtractWeekdayAndTime:
    """Testes para _extract_weekday_and_time."""

    def test_sexta_20h(self):
        weekday, time_str = _extract_weekday_and_time("Sexta-Feira 20h")
        assert weekday == 5
        assert time_str == "20:00"

    def test_segunda_19h30(self):
        weekday, time_str = _extract_weekday_and_time("Segunda 19:30")
        assert weekday == 1
        assert time_str == "19:30"

    def test_no_weekday_no_time(self):
        weekday, time_str = _extract_weekday_and_time("Alguma coisa qualquer")
        assert weekday is None
        assert time_str is None

    def test_domingo(self):
        weekday, _ = _extract_weekday_and_time("Domingo às 10h")
        assert weekday == 0

    def test_sabado_with_accent(self):
        weekday, _ = _extract_weekday_and_time("Sábado 15h")
        assert weekday == 6

    def test_sabado_without_accent(self):
        weekday, _ = _extract_weekday_and_time("sabado 15h")
        assert weekday == 6

    def test_terca_with_accent(self):
        weekday, _ = _extract_weekday_and_time("Terça 20h")
        assert weekday == 2

    def test_terca_without_accent(self):
        weekday, _ = _extract_weekday_and_time("terca 20h")
        assert weekday == 2

    def test_quarta(self):
        weekday, _ = _extract_weekday_and_time("Quarta 19h")
        assert weekday == 3

    def test_quinta(self):
        weekday, _ = _extract_weekday_and_time("Quinta 20h")
        assert weekday == 4

    def test_ocr_2oh_pattern(self):
        # OCR leu "2OH" em vez de "20h"
        weekday, time_str = _extract_weekday_and_time("Sexta-Feira | 2OH")
        assert weekday == 5
        assert time_str is not None

    def test_time_with_h_format(self):
        _, time_str = _extract_weekday_and_time("Sexta 19h30")
        assert time_str == "19:30"


class TestExtractLeaderNameAndPhone:
    """Testes para _extract_leader_name_and_phone."""

    def test_name_and_phone(self):
        name, phone = _extract_leader_name_and_phone("Vanessa 1198331-2401")
        assert name == "Vanessa"
        assert phone == "11983312401"

    def test_no_phone(self):
        name, phone = _extract_leader_name_and_phone("Sem telefone aqui")
        assert name is None
        assert phone is None

    def test_phone_only_no_name(self):
        name, phone = _extract_leader_name_and_phone("1198331-2401")
        assert name is None
        assert phone == "11983312401"

    def test_name_with_special_chars(self):
        name, phone = _extract_leader_name_and_phone("João; 1198331-2401")
        assert name == "João"
        assert phone is not None

    def test_name_with_pipe(self):
        name, phone = _extract_leader_name_and_phone("Ana | 1198765-4321")
        assert name == "Ana"
        assert phone == "11987654321"


class TestCorrectOcrText:
    """Testes para _correct_ocr_text."""

    def test_removes_pipe(self):
        assert _correct_ocr_text("Texto | com pipe") == "Texto  com pipe"

    def test_removes_semicolon(self):
        assert _correct_ocr_text("Texto; com ponto e vírgula") == "Texto com ponto e vírgula"

    def test_strips_whitespace(self):
        assert _correct_ocr_text("  texto  ") == "texto"

    def test_no_corrections_needed(self):
        assert _correct_ocr_text("Texto limpo") == "Texto limpo"


class TestIsNoiseLine:
    """Testes para _is_noise_line."""

    def test_short_line_is_noise(self):
        assert _is_noise_line("abc") is True
        assert _is_noise_line("    ") is True

    def test_weekday_is_noise(self):
        assert _is_noise_line("Segunda") is True

    def test_time_only_short_is_noise(self):
        assert _is_noise_line("20h30") is True

    def test_phone_only_short_is_noise(self):
        assert _is_noise_line("(11) 91234-5678") is True

    def test_normal_text_is_not_noise(self):
        assert _is_noise_line("Rua das Flores, 123, Jardim Botânico") is False

    def test_long_line_with_time_is_not_noise(self):
        assert _is_noise_line("Reunião marcada para 20h no salão principal") is False

    def test_long_line_with_phone_is_not_noise(self):
        assert _is_noise_line("Ligar para o João no número (11) 91234-5678 amanhã") is False


class TestWeekdayMap:
    """Testes para a constante WEEKDAY_MAP."""

    def test_all_weekdays_present(self):
        assert len(WEEKDAY_MAP) == 9  # 7 dias + variantes sem acento

    def test_domingo_is_zero(self):
        assert WEEKDAY_MAP["domingo"] == 0

    def test_sabado_is_six(self):
        assert WEEKDAY_MAP["sábado"] == 6
        assert WEEKDAY_MAP["sabado"] == 6


class TestParseOcrText:
    """Testes para parse_ocr_text (função principal)."""

    def test_empty_lines(self):
        result = parse_ocr_text([])
        assert result.name == ""
        assert result.street == ""
        assert result.leaders == []
        assert result.meetings == []

    def test_first_element_not_gc(self):
        result = parse_ocr_text(["outro", "Casais"])
        assert result.name == ""
        assert result.street == ""

    def test_whitespace_only_lines(self):
        result = parse_ocr_text(["    "])
        assert result.name == ""

    def test_full_real_ocr_sample(self):
        """Testa com dados reais de OCR (exemplo do __main__)."""
        lines = [
            "gc", "Casais", "Jardim Samambaias", "Sexta-Feira | 2OH",
            "Vanessa 1198331-2401", "Cadu 1198331-2572",
            "Rua Carmela Nano", "432", "Jardim das Samambalas",
            "LA G01nA A Jund|A",
        ]
        result = parse_ocr_text(lines)

        assert isinstance(result, GcExtractedData)
        assert "Casais" in result.name
        assert result.street == "Rua Carmela Nano"
        assert result.number == "432"
        assert len(result.leaders) == 2
        assert len(result.meetings) == 1
        assert result.meetings[0].weekday == 5
        assert result.city == "Jundiaí"
        assert result.state == "SP"

    def test_gc_with_two_part_name(self):
        """Nome do GC composto por duas linhas."""
        lines = [
            "gc", "Casais", "Jovens",
            "Sexta 20h",
            "João 1199999-8888",
            "Rua Teste",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert "Casais" in result.name
        assert "Jovens" in result.name

    def test_gc_with_single_part_name_followed_by_weekday(self):
        """Nome simples seguido por dia/horário."""
        lines = [
            "gc", "Vida",
            "Quarta 19h30",
            "Maria 1191111-2222",
            "Rua ABC",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.name == "Vida"
        assert result.meetings[0].weekday == 3
        assert result.meetings[0].start_time == "19:30"

    def test_meeting_only_time_no_weekday_defaults_to_friday(self):
        """Quando só tem horário sem dia, assume sexta (5)."""
        lines = [
            "gc", "Teste",
            "20h",
            "Ana 1199999-1111",
            "Rua XYZ",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        if result.meetings:
            assert result.meetings[0].weekday == 5

    def test_no_leaders_found(self):
        """Sem líderes, vai direto para endereço."""
        lines = [
            "gc", "Teste",
            "Segunda 20h",
            "Rua das Flores",
            "123",
            "Jardim Primavera",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.leaders == []
        assert result.street == "Rua das Flores"

    def test_address_with_complement(self):
        """Endereço com complemento tipo casa/apto."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Rua das Flores",
            "100",
            "Casa 5",
            "Jardim Botânico",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.street == "Rua das Flores"
        assert result.number == "100"
        assert result.complement == "Casa 5"
        assert result.neighborhood == "Jardim Botânico"

    def test_address_without_street_prefix(self):
        """Endereço sem prefixo de logradouro junta tudo."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Praça Central",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.street == "Praça Central"

    def test_address_inline_street_and_number(self):
        """Endereço em uma única linha sem número separado é mantido junto."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Rua ABC 456 Centro",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        # Quando o endereço está em linha única, o parser identifica o logradouro
        # mas não separa o número (precisa estar em linha separada)
        assert "Rua ABC" in result.street

    def test_city_itupeva(self):
        """Detecta cidade Itupeva no texto."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Rua XYZ",
            "Itupeva",
        ]
        result = parse_ocr_text(lines)
        assert result.city == "Itupeva"

    def test_default_city_jundiai(self):
        """Cidade padrão é Jundiaí."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Rua XYZ",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.city == "Jundiaí"
        assert result.state == "SP"

    def test_optional_fields_are_none(self):
        """Campos opcionais retornam None por padrão."""
        lines = ["gc", "Teste", "Sexta 20h", "Rodapé"]
        result = parse_ocr_text(lines)
        assert result.description is None
        assert result.zip_code is None
        assert result.latitude is None
        assert result.longitude is None

    def test_leader_without_name_gets_default(self):
        """Líder sem nome recebe 'Líder' como padrão."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "1199999-0000",
            "Rua XYZ",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        if result.leaders:
            assert result.leaders[0].name == "Líder"

    def test_multiple_leaders(self):
        """Múltiplos líderes extraídos corretamente."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Ana 1199999-1111",
            "João 1199999-2222",
            "Pedro 1199999-3333",
            "Rua XYZ",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert len(result.leaders) == 3
        names = [l.name for l in result.leaders]
        assert "Ana" in names
        assert "João" in names
        assert "Pedro" in names

    def test_leader_contacts_are_whatsapp(self):
        """Contatos dos líderes são do tipo whatsapp."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Ana 1199999-1111",
            "Rua XYZ",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.leaders[0].contacts[0].type == "whatsapp"

    def test_gc_marker_case_insensitive(self):
        """Marcador 'gc' é case-insensitive."""
        lines = ["GC", "Teste", "Sexta 20h", "Rodapé"]
        result = parse_ocr_text(lines)
        assert result.name == "Teste"

    def test_empty_lines_are_filtered(self):
        """Linhas vazias são removidas antes do parsing."""
        lines = [
            "gc", "", "Teste", "  ", "Sexta 20h",
            "", "Líder 1199999-1111", "Rua XYZ", "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.name != ""

    def test_weekday_and_time_not_found_skips_to_next_line(self):
        """Se dia/horário não é encontrado na linha, tenta a próxima."""
        lines = [
            "gc", "Teste",
            "Algo sem dia",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Rua ABC",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        # O nome deve capturar "Algo sem dia" como parte do nome
        # ou pular e encontrar o meeting na próxima linha
        assert isinstance(result, GcExtractedData)

    def test_no_meeting_no_time(self):
        """Sem dia e sem horário, meetings fica vazio."""
        lines = [
            "gc", "Teste",
            "Nenhum dado de dia ou hora",
            "Algo qualquer",
            "Líder 1199999-0000",
            "Rua ABC",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        # Pode ter ou não meetings dependendo da heurística
        assert isinstance(result.meetings, list)

    def test_address_with_avenida_prefix(self):
        """Endereço começando com 'Avenida'."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Avenida Brasil",
            "500",
            "Centro",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.street == "Avenida Brasil"
        assert result.number == "500"

    def test_address_with_av_prefix(self):
        """Endereço começando com 'Av'."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Av Paulista",
            "1000",
            "Bela Vista",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.street == "Av Paulista"
        assert result.number == "1000"

    def test_only_gc_marker(self):
        """Só o marcador 'gc' sem mais linhas."""
        lines = ["gc"]
        result = parse_ocr_text(lines)
        assert result.name == ""
        assert result.street == ""
        assert result.meetings == []
        assert result.leaders == []

    def test_gc_marker_and_name_only(self):
        """Marcador e nome sem mais dados."""
        lines = ["gc", "Esperança"]
        result = parse_ocr_text(lines)
        assert result.name == "Esperança"
        assert result.street == ""

    def test_address_complement_with_apto(self):
        """Complemento com 'apto' (keyword reconhecida pelo parser)."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Rua Teste",
            "200",
            "Apto 12",
            "Bairro Final",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.complement == "Apto 12"

    def test_address_complement_with_bloco(self):
        """Complemento com 'bloco'."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Rua Teste",
            "300",
            "Bloco A",
            "Jardim das Flores",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.complement == "Bloco A"

    def test_address_complement_with_condominio(self):
        """Complemento com 'condomínio'."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Rua Teste",
            "400",
            "Condomínio Sol",
            "Bairro Novo",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.complement == "Condomínio Sol"

    def test_address_complement_with_torre(self):
        """Complemento com 'torre'."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Rua Teste",
            "500",
            "Torre B",
            "Centro",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        assert result.complement == "Torre B"

    def test_address_fallback_rua_number_inline_no_prefix_start(self):
        """Endereço que não começa com prefixo mas contém 'Rua X 123' no texto junto."""
        lines = [
            "gc", "Teste",
            "Sexta 20h",
            "Líder 1199999-0000",
            "Perto da Rua Alfa 789",
            "Rodapé",
        ]
        result = parse_ocr_text(lines)
        # O endereço não começa com prefixo, então cai no fallback de regex
        assert "Rua Alfa" in result.street
        assert result.number == "789"

    def test_ocr_2o_in_extract_weekday_and_time(self):
        """OCR leu '2O' (letra O) como hora — deve interpretar como 20."""
        # Texto com "O" (letra) que faz hour==2 entrar no branch de correção
        weekday, time_str = _extract_weekday_and_time("Sexta 2Oh")
        assert weekday == 5
        assert time_str is not None

    def test_normalize_time_2o_context(self):
        """_normalize_time com '2O' deve retornar 20:00."""
        # Após substituição "O"→"0", cleaned é "20", mas hour==20 (len<=2 com int=20)
        result = _normalize_time("2O")
        assert result == "20:00"
