"""Testes unitários dos métodos to_sse() dos schemas SSE."""

import json

from faker import Faker

from app.schemas.gc_image_import import (
    GcExtractedData,
    GcHeartbeatEvent,
    GcJobStatusEvent,
)

fake = Faker()


class TestGcJobStatusEventSse:
    """Testa o método to_sse() de GcJobStatusEvent."""

    def test_basic_format(self):
        """Deve retornar o formato SSE correto: 'event: ...\ndata: ...\n\n'."""
        event = GcJobStatusEvent(status="done")
        result = event.to_sse()
        assert result.startswith("event: status\n")
        assert "data: " in result
        assert result.endswith("\n\n")

    def test_custom_event_name(self):
        """O nome do evento pode ser customizado."""
        event = GcJobStatusEvent(status="processing")
        result = event.to_sse(event="custom")
        assert "event: custom\n" in result

    def test_data_is_valid_json(self):
        """O campo data deve conter JSON válido."""
        event = GcJobStatusEvent(status="pending", progress="Lendo imagem 1/2")
        result = event.to_sse()
        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        parsed = json.loads(data_line[len("data: "):])
        assert parsed["status"] == "pending"
        assert parsed["progress"] == "Lendo imagem 1/2"

    def test_none_fields_excluded(self):
        """Campos None devem ser excluídos do JSON (exclude_none=True)."""
        event = GcJobStatusEvent(status="done")
        result = event.to_sse()
        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        parsed = json.loads(data_line[len("data: "):])
        assert "progress" not in parsed
        assert "result" not in parsed
        assert "error" not in parsed

    def test_unicode_characters_preserved(self):
        """Caracteres unicode (acentos pt-BR) devem ser preservados."""
        event = GcJobStatusEvent(status="failed", error="Extração falhou")
        result = event.to_sse()
        assert "Extração" in result
        assert "\\u" not in result

    def test_with_result_data(self):
        """Dados de resultado devem ser serializados corretamente."""
        extracted = GcExtractedData(
            name=fake.company(),
            street=fake.street_address(),
        )
        event = GcJobStatusEvent(status="done", result=[extracted])
        result = event.to_sse()
        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        parsed = json.loads(data_line[len("data: "):])
        assert parsed["status"] == "done"
        assert len(parsed["result"]) == 1
        assert parsed["result"][0]["name"] == extracted.name

    def test_double_newline_terminator(self):
        """SSE requer terminação com \\n\\n entre eventos."""
        event = GcJobStatusEvent(status="pending")
        result = event.to_sse()
        assert result[-2:] == "\n\n"

    def test_no_extra_newlines_in_middle(self):
        """Não deve haver linhas vazias entre event e data."""
        event = GcJobStatusEvent(status="done")
        result = event.to_sse()
        lines = result.rstrip("\n").split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("event: ")
        assert lines[1].startswith("data: ")


class TestGcHeartbeatEventSse:
    """Testa o método to_sse() de GcHeartbeatEvent."""

    def test_basic_format(self):
        """Deve usar event: heartbeat."""
        heartbeat = GcHeartbeatEvent(ts="2026-03-20T12:00:00+00:00")
        result = heartbeat.to_sse()
        assert "event: heartbeat\n" in result

    def test_data_contains_ts(self):
        """O campo data deve conter o timestamp."""
        ts = "2026-03-20T12:00:00+00:00"
        heartbeat = GcHeartbeatEvent(ts=ts)
        result = heartbeat.to_sse()
        data_line = [line for line in result.split("\n") if line.startswith("data: ")][0]
        parsed = json.loads(data_line[len("data: "):])
        assert parsed["ts"] == ts

    def test_double_newline_terminator(self):
        """SSE requer terminação com \\n\\n."""
        heartbeat = GcHeartbeatEvent(ts="2026-03-20T12:00:00+00:00")
        result = heartbeat.to_sse()
        assert result[-2:] == "\n\n"
