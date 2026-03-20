"""Testes da rota GET /api/v1/gcs/import/jobs/{job_id}/stream — SSE de progresso."""

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from faker import Faker

fake = Faker()

STREAM_ENDPOINT = "/api/v1/gcs/import/jobs/{job_id}/stream"


def _parse_sse_events(raw_text: str) -> list[dict]:
    """Extrai eventos SSE do texto bruto da resposta."""
    events = []
    for block in raw_text.strip().split("\n\n"):
        event_type = None
        data = None
        for line in block.strip().split("\n"):
            if line.startswith("event: "):
                event_type = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if event_type and data is not None:
            events.append({"event": event_type, "data": data})
    return events


class TestStreamJobNotFound:
    """Testa que job inexistente retorna 404."""

    @patch("app.routers.gc_image_import.get_job_state", new_callable=AsyncMock)
    def test_unknown_job_returns_404(self, mock_get_state, client):
        """Job que não existe no Redis deve retornar 404."""
        mock_get_state.return_value = None
        job_id = str(uuid.uuid4())
        resp = client.get(STREAM_ENDPOINT.format(job_id=job_id))
        assert resp.status_code == 404
        assert "não encontrado" in resp.json()["detail"].lower()


class TestStreamJobDone:
    """Testa SSE quando o job finaliza com sucesso."""

    @patch("app.routers.gc_image_import.get_job_state", new_callable=AsyncMock)
    def test_done_emits_status_done_and_closes(self, mock_get_state, client):
        """Quando o status é 'done', deve emitir evento com resultado e encerrar."""
        fake_result = {
            "name": fake.company(),
            "street": fake.street_address(),
        }
        mock_get_state.return_value = {
            "status": "done",
            "progress": "100%",
            "result": fake_result,
        }
        job_id = str(uuid.uuid4())
        resp = client.get(STREAM_ENDPOINT.format(job_id=job_id))
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"

        events = _parse_sse_events(resp.text)
        assert len(events) >= 1
        last_event = events[-1]
        assert last_event["event"] == "status"
        assert last_event["data"]["status"] == "done"
        assert last_event["data"]["result"] == fake_result


class TestStreamJobFailed:
    """Testa SSE quando o job falha."""

    @patch("app.routers.gc_image_import.get_job_state", new_callable=AsyncMock)
    def test_failed_emits_status_failed_and_closes(self, mock_get_state, client):
        """Quando o status é 'failed', deve emitir evento com erro e encerrar."""
        error_msg = fake.sentence()
        mock_get_state.return_value = {
            "status": "failed",
            "progress": None,
            "error": error_msg,
        }
        job_id = str(uuid.uuid4())
        resp = client.get(STREAM_ENDPOINT.format(job_id=job_id))
        assert resp.status_code == 200

        events = _parse_sse_events(resp.text)
        last_event = events[-1]
        assert last_event["event"] == "status"
        assert last_event["data"]["status"] == "failed"
        assert last_event["data"]["error"] == error_msg


class TestStreamJobProgress:
    """Testa SSE com atualizações de progresso."""

    @patch("app.routers.gc_image_import.get_job_state", new_callable=AsyncMock)
    def test_progress_then_done(self, mock_get_state, client):
        """Deve emitir eventos de progresso antes do done."""
        mock_get_state.side_effect = [
            # Chamada inicial (verificação de existência)
            {"status": "processing", "progress": "50%"},
            # Primeira iteração do loop
            {"status": "processing", "progress": "50%"},
            # Segunda iteração — muda progresso
            {"status": "processing", "progress": "80%"},
            # Terceira iteração — finaliza
            {"status": "done", "progress": "100%", "result": {"name": fake.company()}},
        ]
        job_id = str(uuid.uuid4())
        resp = client.get(STREAM_ENDPOINT.format(job_id=job_id))
        assert resp.status_code == 200

        events = _parse_sse_events(resp.text)
        statuses = [e["data"]["status"] for e in events if e["event"] == "status"]
        assert "processing" in statuses
        assert statuses[-1] == "done"

    @patch("app.routers.gc_image_import.get_job_state", new_callable=AsyncMock)
    def test_job_expires_during_stream(self, mock_get_state, client):
        """Se o job expirar durante o stream, deve emitir failed e encerrar."""
        mock_get_state.side_effect = [
            # Chamada inicial
            {"status": "processing", "progress": "30%"},
            # Primeira iteração do loop
            {"status": "processing", "progress": "30%"},
            # Segunda iteração — job desapareceu
            None,
        ]
        job_id = str(uuid.uuid4())
        resp = client.get(STREAM_ENDPOINT.format(job_id=job_id))
        assert resp.status_code == 200

        events = _parse_sse_events(resp.text)
        last_event = events[-1]
        assert last_event["data"]["status"] == "failed"
        assert "expirado" in last_event["data"]["error"].lower()


class TestStreamResponseHeaders:
    """Testa os headers corretos para SSE."""

    @patch("app.routers.gc_image_import.get_job_state", new_callable=AsyncMock)
    def test_sse_headers(self, mock_get_state, client):
        """A resposta deve conter headers para SSE e sem buffering."""
        mock_get_state.return_value = {
            "status": "done",
            "progress": "100%",
            "result": {},
        }
        job_id = str(uuid.uuid4())
        resp = client.get(STREAM_ENDPOINT.format(job_id=job_id))
        assert "text/event-stream" in resp.headers["content-type"]
        assert resp.headers.get("cache-control") == "no-cache"
