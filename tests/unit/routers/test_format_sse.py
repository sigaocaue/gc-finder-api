"""Testes unitários do helper _format_sse."""

import json

from faker import Faker

from app.routers.gc_image_import import _format_sse

fake = Faker()


class TestFormatSse:
    """Testa a função utilitária _format_sse."""

    def test_basic_format(self):
        """Deve retornar o formato SSE correto: 'event: ...\ndata: ...\n\n'."""
        result = _format_sse("status", {"status": "done"})
        assert result.startswith("event: status\n")
        assert "data: " in result
        assert result.endswith("\n\n")

    def test_event_name_preserved(self):
        """O nome do evento deve ser preservado na saída."""
        event_name = fake.word()
        result = _format_sse(event_name, {"key": "value"})
        assert f"event: {event_name}\n" in result

    def test_data_is_valid_json(self):
        """O campo data deve conter JSON válido."""
        data = {"name": fake.name(), "count": fake.random_int()}
        result = _format_sse("test", data)
        data_line = [l for l in result.split("\n") if l.startswith("data: ")][0]
        parsed = json.loads(data_line[len("data: "):])
        assert parsed == data

    def test_unicode_characters_preserved(self):
        """Caracteres unicode (acentos pt-BR) devem ser preservados."""
        data = {"message": "Extração concluída com sucesso"}
        result = _format_sse("status", data)
        assert "Extração" in result
        assert "\\u" not in result

    def test_empty_data_dict(self):
        """Dict vazio deve ser serializado como '{}'."""
        result = _format_sse("heartbeat", {})
        assert "data: {}" in result

    def test_nested_data(self):
        """Dados aninhados devem ser serializados corretamente."""
        data = {
            "status": "done",
            "result": {
                "name": fake.company(),
                "leaders": [{"name": fake.name()}],
            },
        }
        result = _format_sse("status", data)
        data_line = [l for l in result.split("\n") if l.startswith("data: ")][0]
        parsed = json.loads(data_line[len("data: "):])
        assert parsed["result"]["leaders"][0]["name"] == data["result"]["leaders"][0]["name"]

    def test_double_newline_terminator(self):
        """SSE requer terminação com \\n\\n entre eventos."""
        result = _format_sse("test", {"a": 1})
        assert result[-2:] == "\n\n"

    def test_no_extra_newlines_in_middle(self):
        """Não deve haver linhas vazias entre event e data."""
        result = _format_sse("test", {"a": 1})
        lines = result.rstrip("\n").split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("event: ")
        assert lines[1].startswith("data: ")
