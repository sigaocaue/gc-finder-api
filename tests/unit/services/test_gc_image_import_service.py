"""Testes unitários do serviço de importação de GC por imagem."""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from faker import Faker

from app.services.gc_image_import_service import (
    ALLOWED_EXTENSIONS,
    JOB_KEY_PREFIX,
    JOB_TTL_SECONDS,
    MAX_IMAGE_SIZE,
    _job_key,
    _set_job_state,
    get_job_state,
    process_image_job,
    start_job,
)

fake = Faker()


# ---------------------------------------------------------------------------
# _job_key
# ---------------------------------------------------------------------------


class TestJobKey:
    """Testa a geração da chave Redis do job."""

    def test_returns_prefixed_key(self):
        job_id = "abc-123"
        assert _job_key(job_id) == f"{JOB_KEY_PREFIX}:abc-123"

    def test_different_ids_produce_different_keys(self):
        assert _job_key("a") != _job_key("b")


# ---------------------------------------------------------------------------
# _set_job_state
# ---------------------------------------------------------------------------


class TestSetJobState:
    """Testa a persistência do estado do job no Redis."""

    @pytest.mark.asyncio
    async def test_sets_state_with_ttl(self):
        """Deve salvar o estado no Redis com TTL correto."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)

        await _set_job_state(
            redis_mock, "job-1", status="pending", created_at="2026-01-01T00:00:00"
        )

        redis_mock.set.assert_called_once()
        args, kwargs = redis_mock.set.call_args
        key = args[0]
        state = json.loads(args[1])
        assert key == _job_key("job-1")
        assert state["status"] == "pending"
        assert state["job_id"] == "job-1"
        assert state["created_at"] == "2026-01-01T00:00:00"
        assert kwargs["ex"] == JOB_TTL_SECONDS

    @pytest.mark.asyncio
    async def test_preserves_created_at_from_existing_state(self):
        """Deve preservar created_at do estado anterior quando não informado."""
        existing = json.dumps({"created_at": "2026-01-01T12:00:00"})
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=existing)

        await _set_job_state(redis_mock, "job-1", status="processing")

        state = json.loads(redis_mock.set.call_args[0][1])
        assert state["created_at"] == "2026-01-01T12:00:00"

    @pytest.mark.asyncio
    async def test_stores_progress_and_error(self):
        """Deve armazenar campos progress e error."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)

        await _set_job_state(
            redis_mock,
            "job-1",
            status="failed",
            progress="Etapa 2",
            error="Algo deu errado",
            created_at="2026-01-01T00:00:00",
        )

        state = json.loads(redis_mock.set.call_args[0][1])
        assert state["progress"] == "Etapa 2"
        assert state["error"] == "Algo deu errado"

    @pytest.mark.asyncio
    async def test_stores_result_dict(self):
        """Deve armazenar o resultado como dicionário."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        result = {"name": "GC Teste", "street": "Rua A"}

        await _set_job_state(
            redis_mock,
            "job-1",
            status="done",
            result=result,
            created_at="2026-01-01T00:00:00",
        )

        state = json.loads(redis_mock.set.call_args[0][1])
        assert state["result"] == result


# ---------------------------------------------------------------------------
# get_job_state
# ---------------------------------------------------------------------------


class TestGetJobState:
    """Testa a leitura do estado de um job no Redis."""

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    async def test_returns_state_when_exists(self, mock_get_redis):
        """Deve retornar o estado do job quando existir no Redis."""
        expected = {"job_id": "j1", "status": "done"}
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=json.dumps(expected))
        mock_get_redis.return_value = redis_mock

        result = await get_job_state("j1")

        assert result == expected
        redis_mock.aclose.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    async def test_returns_none_when_not_found(self, mock_get_redis):
        """Deve retornar None quando o job não existir."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        result = await get_job_state("inexistente")

        assert result is None
        redis_mock.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# start_job
# ---------------------------------------------------------------------------


class TestStartJob:
    """Testa a criação de um novo job."""

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    async def test_returns_uuid_string(self, mock_get_redis):
        """Deve retornar um UUID válido como job_id."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        job_id = await start_job([Path("/tmp/img.png")], [])

        # Verifica que é um UUID válido
        uuid.UUID(job_id)

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    async def test_saves_pending_state(self, mock_get_redis):
        """Deve salvar o estado inicial como pending no Redis."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        await start_job([], ["https://example.com/img.jpg"])

        redis_mock.set.assert_called_once()
        state = json.loads(redis_mock.set.call_args[0][1])
        assert state["status"] == "pending"

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    async def test_closes_redis_connection(self, mock_get_redis):
        """Deve fechar a conexão Redis após uso."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        await start_job([], [])

        redis_mock.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# process_image_job — download de URLs
# ---------------------------------------------------------------------------


class TestProcessImageJobUrlDownload:
    """Testa o download de imagens por URL."""

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch("app.services.gc_image_import_service.httpx.AsyncClient")
    async def test_failed_url_download_sets_failed_state(
        self, mock_http_cls, mock_get_redis
    ):
        """Falha no download deve marcar o job como failed."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        # Simula erro de rede no download
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
        mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        await process_image_job("job-1", [], ["https://example.com/img.jpg"])

        # Verifica que o último set no Redis foi com status=failed
        last_set_call = redis_mock.set.call_args_list[-1]
        state = json.loads(last_set_call[0][1])
        assert state["status"] == "failed"
        assert "url" in state["error"].lower()

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch("app.services.gc_image_import_service.httpx.AsyncClient")
    async def test_url_extension_detection(self, mock_http_cls, mock_get_redis):
        """Deve detectar extensão .png na URL."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        mock_response = MagicMock()
        mock_response.content = b"\x89PNG\r\n\x1a\n"
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_http_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_http_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "app.services.gc_image_import_service.extract_text",
            new_callable=AsyncMock,
            return_value=[],
        ):
            await process_image_job("job-1", [], ["https://example.com/foto.png"])

        # O job deve ter falhado no OCR (sem texto), mas o download funcionou
        last_state = json.loads(redis_mock.set.call_args_list[-1][0][1])
        assert last_state["status"] == "failed"
        assert "nenhum texto" in last_state["error"].lower()


# ---------------------------------------------------------------------------
# process_image_job — fluxo sem imagens
# ---------------------------------------------------------------------------


class TestProcessImageJobNoImages:
    """Testa o comportamento quando não há imagens disponíveis."""

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    async def test_no_images_sets_failed(self, mock_get_redis):
        """Sem imagens disponíveis deve marcar o job como failed."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        await process_image_job("job-1", [], [])

        last_state = json.loads(redis_mock.set.call_args_list[-1][0][1])
        assert last_state["status"] == "failed"
        assert "nenhuma imagem" in last_state["error"].lower()


# ---------------------------------------------------------------------------
# process_image_job — OCR sem resultado
# ---------------------------------------------------------------------------


class TestProcessImageJobOcrEmpty:
    """Testa o comportamento quando o OCR não retorna texto."""

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch(
        "app.services.gc_image_import_service.extract_text",
        new_callable=AsyncMock,
        return_value=[],
    )
    async def test_empty_ocr_sets_failed(self, mock_ocr, mock_get_redis):
        """Nenhum texto detectado deve marcar o job como failed."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        await process_image_job("job-1", [Path("/tmp/img.png")], [])

        last_state = json.loads(redis_mock.set.call_args_list[-1][0][1])
        assert last_state["status"] == "failed"
        assert "nenhum texto" in last_state["error"].lower()


# ---------------------------------------------------------------------------
# process_image_job — parsing sem dados mínimos
# ---------------------------------------------------------------------------


class TestProcessImageJobParsingIncomplete:
    """Testa quando o parsing não extrai nome ou endereço."""

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch("app.services.gc_image_import_service.extract_text", new_callable=AsyncMock)
    @patch("app.services.gc_image_import_service.parse_ocr_text")
    async def test_missing_name_sets_failed(
        self, mock_parse, mock_ocr, mock_get_redis
    ):
        """Sem nome extraído deve marcar o job como failed."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock
        mock_ocr.return_value = ["algum texto"]
        mock_parse.return_value = MagicMock(name="", street="Rua A")

        await process_image_job("job-1", [Path("/tmp/img.png")], [])

        last_state = json.loads(redis_mock.set.call_args_list[-1][0][1])
        assert last_state["status"] == "failed"
        assert "nome" in last_state["error"].lower()

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch("app.services.gc_image_import_service.extract_text", new_callable=AsyncMock)
    @patch("app.services.gc_image_import_service.parse_ocr_text")
    async def test_missing_street_sets_failed(
        self, mock_parse, mock_ocr, mock_get_redis
    ):
        """Sem endereço extraído deve marcar o job como failed."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock
        mock_ocr.return_value = ["algum texto"]
        mock_parse.return_value = MagicMock(name="GC Teste", street="")

        await process_image_job("job-1", [Path("/tmp/img.png")], [])

        last_state = json.loads(redis_mock.set.call_args_list[-1][0][1])
        assert last_state["status"] == "failed"


# ---------------------------------------------------------------------------
# process_image_job — fluxo completo com sucesso
# ---------------------------------------------------------------------------


class TestProcessImageJobSuccess:
    """Testa o fluxo completo de sucesso."""

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch("app.services.gc_image_import_service.extract_text", new_callable=AsyncMock)
    @patch("app.services.gc_image_import_service.parse_ocr_text")
    @patch(
        "app.services.gc_image_import_service.fetch_coordinates",
        new_callable=AsyncMock,
    )
    async def test_full_success_flow(
        self, mock_geocoding, mock_parse, mock_ocr, mock_get_redis
    ):
        """Fluxo completo deve terminar com status=done e resultado."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        mock_ocr.return_value = ["GC Central - Rua A, 100"]

        from app.schemas.gc_image_import import GcExtractedData

        extracted = GcExtractedData(
            name="GC Central",
            street="Rua A",
            number="100",
            neighborhood="Centro",
            city="Jundiaí",
            state="SP",
        )
        mock_parse.return_value = extracted
        mock_geocoding.return_value = (-23.185, -46.897)

        await process_image_job("job-1", [Path("/tmp/img.png")], [])

        last_state = json.loads(redis_mock.set.call_args_list[-1][0][1])
        assert last_state["status"] == "done"
        assert last_state["result"]["name"] == "GC Central"
        assert last_state["result"]["latitude"] == -23.185
        assert last_state["result"]["longitude"] == -46.897

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch("app.services.gc_image_import_service.extract_text", new_callable=AsyncMock)
    @patch("app.services.gc_image_import_service.parse_ocr_text")
    @patch(
        "app.services.gc_image_import_service.fetch_coordinates",
        new_callable=AsyncMock,
    )
    async def test_success_without_coordinates(
        self, mock_geocoding, mock_parse, mock_ocr, mock_get_redis
    ):
        """Deve concluir com sucesso mesmo sem coordenadas."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        mock_ocr.return_value = ["GC Norte"]

        from app.schemas.gc_image_import import GcExtractedData

        extracted = GcExtractedData(
            name="GC Norte", street="Rua B", city="Jundiaí", state="SP"
        )
        mock_parse.return_value = extracted
        mock_geocoding.return_value = None

        await process_image_job("job-1", [Path("/tmp/img.png")], [])

        last_state = json.loads(redis_mock.set.call_args_list[-1][0][1])
        assert last_state["status"] == "done"
        assert last_state["result"]["latitude"] is None

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch("app.services.gc_image_import_service.extract_text", new_callable=AsyncMock)
    @patch("app.services.gc_image_import_service.parse_ocr_text")
    @patch(
        "app.services.gc_image_import_service.fetch_coordinates",
        new_callable=AsyncMock,
    )
    async def test_progress_updates_sequence(
        self, mock_geocoding, mock_parse, mock_ocr, mock_get_redis
    ):
        """Deve atualizar o progresso em cada etapa do processamento."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        mock_ocr.return_value = ["texto"]

        from app.schemas.gc_image_import import GcExtractedData

        extracted = GcExtractedData(
            name="GC", street="Rua X", city="Jundiaí", state="SP"
        )
        mock_parse.return_value = extracted
        mock_geocoding.return_value = (-23.0, -46.0)

        await process_image_job("job-1", [Path("/tmp/img.png")], [])

        # Coleta todos os estados salvos no Redis
        all_states = [
            json.loads(call[0][1]) for call in redis_mock.set.call_args_list
        ]
        statuses = [s["status"] for s in all_states]

        assert "processing" in statuses
        assert "done" in statuses
        # processing deve vir antes de done
        assert statuses.index("processing") < statuses.index("done")


# ---------------------------------------------------------------------------
# process_image_job — tratamento de exceção genérica
# ---------------------------------------------------------------------------


class TestProcessImageJobException:
    """Testa o tratamento de exceções inesperadas."""

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch("app.services.gc_image_import_service.extract_text", new_callable=AsyncMock)
    async def test_unexpected_error_sets_failed(self, mock_ocr, mock_get_redis):
        """Exceção inesperada deve marcar o job como failed."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        mock_ocr.side_effect = RuntimeError("Erro inesperado no OCR")

        await process_image_job("job-1", [Path("/tmp/img.png")], [])

        last_state = json.loads(redis_mock.set.call_args_list[-1][0][1])
        assert last_state["status"] == "failed"
        assert "inesperado" in last_state["error"].lower()

    @pytest.mark.asyncio
    @patch("app.services.gc_image_import_service._get_redis")
    @patch("app.services.gc_image_import_service.extract_text", new_callable=AsyncMock)
    async def test_redis_closed_after_exception(self, mock_ocr, mock_get_redis):
        """Deve fechar a conexão Redis mesmo após exceção."""
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=None)
        mock_get_redis.return_value = redis_mock

        mock_ocr.side_effect = RuntimeError("boom")

        await process_image_job("job-1", [Path("/tmp/img.png")], [])

        redis_mock.aclose.assert_called_once()


# ---------------------------------------------------------------------------
# Constantes exportadas
# ---------------------------------------------------------------------------


class TestConstants:
    """Testa que as constantes do módulo estão corretas."""

    def test_allowed_extensions(self):
        assert ALLOWED_EXTENSIONS == {".jpg", ".jpeg", ".png"}

    def test_max_image_size_is_5mb(self):
        assert MAX_IMAGE_SIZE == 5 * 1024 * 1024

    def test_job_ttl_is_one_hour(self):
        assert JOB_TTL_SECONDS == 3600
