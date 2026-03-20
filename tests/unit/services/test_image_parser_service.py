"""Unit tests for the OCR text parser helper."""

from app.schemas.gc_image_import import GcExtractedData, MeetingExtracted
from app.services.image_parser_service import parse_ocr_text


def test_parse_full_description():
    lines = [
        "  GC Esperança  ",
        "Rua das Flores, 123",
        "Casa 5",
        "Jardim Botânico",
        "São Paulo - SP",
        "Segunda 19h",
        "Terça 20:30",
        "Líder Ana",
        "Celular: (11) 91234-5678",
        "Contato: (11) 99876-5432",
    ]

    result = parse_ocr_text(lines)

    assert isinstance(result, GcExtractedData)
    assert result.name == "GC Esperança"
    assert result.street.startswith("Rua das Flores")
    assert result.number == "123"
    assert result.complement == "Casa 5"
    assert result.neighborhood is not None
    assert "São Paulo" in result.city
    assert result.state == "SP"
    assert len(result.meetings) == 2
    assert MeetingExtracted(weekday=1, start_time="19:00") in result.meetings
    assert MeetingExtracted(weekday=2, start_time="20:30") in result.meetings
    assert len(result.leaders) >= 1
    leader_names = [leader.name for leader in result.leaders]
    assert "Líder Ana" in leader_names
    phones = [contact.value for leader in result.leaders for contact in leader.contacts]
    assert "11912345678" in phones
    assert "11998765432" in phones


def test_parse_with_minimal_data_falls_back():
    lines = [
        "    ",
    ]

    result = parse_ocr_text(lines)

    assert result.name == ""
    assert result.street == ""
    assert result.number is None
    assert result.complement is None
    assert result.neighborhood is None
    assert result.city == "Jundiaí"
    assert result.state == "SP"
    assert isinstance(result.leaders, list)
    assert isinstance(result.meetings, list)


def test_parse_generates_default_leaders_when_only_phones():
    lines = [
        "GC Sem Nome",
        "Av. Central, 10",
        "+55 11 91234-5678",
        "(11) 99876-5432",
    ]

    result = parse_ocr_text(lines)

    assert result.name == "GC Sem Nome"
    assert len(result.leaders) == 2
    assert all(leader.name == "Líder" for leader in result.leaders)
    assert {contact.value for leader in result.leaders for contact in leader.contacts} == {
        "11912345678",
        "11998765432",
    }
