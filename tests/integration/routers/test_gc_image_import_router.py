"""Testes da rota POST /api/v1/gcs/import/image — validação de entrada."""

import io
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from faker import Faker

fake = Faker()

ENDPOINT = "/api/v1/gcs/import/image"

# Imagem PNG válida gerada pelo Faker (< 5MB)
FAKE_IMAGE_CONTENT = fake.image(size=(10, 10), image_format="png")


def _make_upload(filename: str, content: bytes = FAKE_IMAGE_CONTENT):
    """Cria tupla no formato esperado pelo TestClient para upload de arquivo."""
    return "images", (filename, io.BytesIO(content), "application/octet-stream")


# ---------------------------------------------------------------------------
# Sem imagem nem URL
# ---------------------------------------------------------------------------


class TestNoInput:
    """Testa que a requisição falha quando nenhuma imagem ou URL é enviada."""

    def test_no_files_no_urls(self, client):
        """Requisição sem arquivos e sem URLs deve retornar 400."""
        resp = client.post(ENDPOINT)
        assert resp.status_code == 400
        assert "pelo menos uma imagem" in resp.json()["detail"].lower()

    def test_empty_files_list(self, client):
        """Enviar lista de arquivos vazia deve retornar 400."""
        resp = client.post(ENDPOINT, files=[])
        assert resp.status_code == 400

    def test_only_whitespace_urls(self, client):
        """URLs contendo apenas espaços devem ser tratadas como vazias."""
        resp = client.post(ENDPOINT, data={"images_urls": ["   ", "  "]})
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Validação de extensão de arquivos
# ---------------------------------------------------------------------------


class TestFileExtensionValidation:
    """Testa validação de extensões de arquivo."""

    @pytest.mark.parametrize("ext", [".gif", ".bmp", ".webp", ".svg", ".pdf", ".tiff"])
    def test_invalid_extension_returns_error(self, client, ext):
        """Extensões não permitidas devem gerar erro."""
        resp = client.post(ENDPOINT, files=[_make_upload(f"foto{ext}")])
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert any("não permitida" in msg.lower() for msg in detail)

    @pytest.mark.parametrize("filename", ["foto.png", "foto.jpg", "foto.jpeg"])
    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_valid_extensions_accepted(self, mock_start, mock_process, client, filename):
        """Extensões .png, .jpg e .jpeg devem ser aceitas."""
        mock_start.return_value = str(uuid.uuid4())
        resp = client.post(ENDPOINT, files=[_make_upload(filename)])
        assert resp.status_code == 202

    def test_multiple_invalid_extensions_all_reported(self, client):
        """Vários arquivos com extensão inválida devem gerar um erro para cada."""
        files = [_make_upload("a.gif"), _make_upload("b.bmp"), _make_upload("c.webp")]
        resp = client.post(ENDPOINT, files=files)
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert len(detail) == 3
        assert any("a.gif" in msg for msg in detail)
        assert any("b.bmp" in msg for msg in detail)
        assert any("c.webp" in msg for msg in detail)


# ---------------------------------------------------------------------------
# Validação de tamanho de arquivos
# ---------------------------------------------------------------------------


class TestFileSizeValidation:
    """Testa validação do tamanho máximo de arquivo (5MB)."""

    def test_file_exceeds_max_size(self, client):
        """Arquivo acima de 5MB deve gerar erro."""
        big_content = b"\x00" * (5 * 1024 * 1024 + 1)
        resp = client.post(ENDPOINT, files=[_make_upload("grande.png", big_content)])
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert any("5mb" in msg.lower() for msg in detail)

    def test_multiple_oversized_files_all_reported(self, client):
        """Vários arquivos acima do limite devem gerar um erro para cada."""
        big = b"\x00" * (5 * 1024 * 1024 + 1)
        files = [_make_upload("a.png", big), _make_upload("b.jpg", big)]
        resp = client.post(ENDPOINT, files=files)
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert len(detail) == 2

    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_file_exactly_at_limit_accepted(self, mock_start, mock_process, client):
        """Arquivo com exatamente 5MB deve ser aceito."""
        mock_start.return_value = str(uuid.uuid4())
        content = b"\x00" * (5 * 1024 * 1024)
        resp = client.post(ENDPOINT, files=[_make_upload("ok.png", content)])
        assert resp.status_code == 202


# ---------------------------------------------------------------------------
# Validação de URLs
# ---------------------------------------------------------------------------


class TestUrlValidation:
    """Testa validação de URLs enviadas no campo images_urls."""

    def test_empty_string_url(self, client):
        """URL vazia deve gerar erro."""
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("ok.png")],
            data={"images_urls": [""]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert any("vazia" in msg.lower() for msg in detail)

    def test_whitespace_only_url(self, client):
        """URL contendo apenas espaços deve gerar erro de URL vazia."""
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("ok.png")],
            data={"images_urls": ["   "]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert any("vazia" in msg.lower() for msg in detail)

    @pytest.mark.parametrize(
        "url",
        [
            "nao-eh-url",
            "ftp://arquivo.com/img.png",
            "arquivo.png",
            "://sem-scheme.com",
            "https://",
            "just-text",
        ],
    )
    def test_invalid_url_format(self, client, url):
        """URLs sem scheme http/https ou sem host devem gerar erro."""
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("ok.png")],
            data={"images_urls": [url]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert any("não é uma url válida" in msg.lower() for msg in detail)

    def test_multiple_invalid_urls_all_reported(self, client):
        """Várias URLs inválidas devem gerar um erro para cada."""
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("ok.png")],
            data={"images_urls": ["invalida", "", "ftp://x.com"]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert len(detail) == 3

    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_valid_http_url_accepted(self, mock_start, mock_process, client):
        """URL http válida deve ser aceita."""
        mock_start.return_value = str(uuid.uuid4())
        resp = client.post(
            ENDPOINT, data={"images_urls": [fake.url(schemes=["http"])]}
        )
        assert resp.status_code == 202

    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_valid_https_url_accepted(self, mock_start, mock_process, client):
        """URL https válida deve ser aceita."""
        mock_start.return_value = str(uuid.uuid4())
        resp = client.post(
            ENDPOINT, data={"images_urls": [fake.url(schemes=["https"])]}
        )
        assert resp.status_code == 202


# ---------------------------------------------------------------------------
# Acumulação de erros (múltiplos tipos)
# ---------------------------------------------------------------------------


class TestErrorAccumulation:
    """Testa que todos os erros são acumulados e retornados juntos."""

    def test_invalid_extension_and_invalid_url(self, client):
        """Erro de extensão e erro de URL devem aparecer juntos."""
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("foto.gif")],
            data={"images_urls": ["nao-eh-url"]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert len(detail) == 2
        assert any("não permitida" in msg.lower() for msg in detail)
        assert any("não é uma url válida" in msg.lower() for msg in detail)

    def test_oversized_file_and_empty_url(self, client):
        """Erro de tamanho e erro de URL vazia devem aparecer juntos."""
        big = b"\x00" * (5 * 1024 * 1024 + 1)
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("grande.png", big)],
            data={"images_urls": [""]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert len(detail) == 2

    def test_all_error_types_combined(self, client):
        """Extensão inválida + tamanho excedido + URL inválida + URL vazia."""
        big = b"\x00" * (5 * 1024 * 1024 + 1)
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("foto.gif"), _make_upload("enorme.png", big)],
            data={"images_urls": ["", "nao-url"]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert len(detail) == 4

    def test_mixed_valid_and_invalid_still_returns_errors(self, client):
        """Mesmo com arquivos válidos, se houver inválidos deve retornar 400."""
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("boa.png"), _make_upload("ruim.gif")],
            data={"images_urls": [fake.url(), "invalida"]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert len(detail) == 2

    def test_error_detail_is_list(self, client):
        """O campo detail da resposta de erro deve ser uma lista."""
        resp = client.post(ENDPOINT, files=[_make_upload("foto.gif")])
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert isinstance(detail, list)

    def test_error_messages_identify_each_file(self, client):
        """Cada mensagem de erro deve identificar o arquivo ou índice correspondente."""
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("a.gif"), _make_upload("b.bmp")],
            data={"images_urls": ["ruim1", "ruim2"]},
        )
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert any("a.gif" in msg for msg in detail)
        assert any("b.bmp" in msg for msg in detail)
        assert any("images_urls[0]" in msg for msg in detail)
        assert any("images_urls[1]" in msg for msg in detail)


# ---------------------------------------------------------------------------
# Caso de sucesso
# ---------------------------------------------------------------------------


class TestSuccessCase:
    """Testa o fluxo de sucesso da rota."""

    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_valid_file_returns_202(self, mock_start, mock_process, client):
        """Upload válido deve retornar 202 com job_id e stream_url."""
        job_id = str(uuid.uuid4())
        mock_start.return_value = job_id
        resp = client.post(ENDPOINT, files=[_make_upload(fake.file_name(extension="jpg"))])
        assert resp.status_code == 202
        body = resp.json()
        assert body["data"]["job_id"] == job_id
        assert body["data"]["status"] == "pending"
        assert f"/jobs/{job_id}/stream" in body["data"]["stream_url"]
        assert body["message"]

    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_valid_url_only_returns_202(self, mock_start, mock_process, client):
        """Enviar apenas URL válida (sem arquivo) deve retornar 202."""
        mock_start.return_value = str(uuid.uuid4())
        resp = client.post(
            ENDPOINT, data={"images_urls": [fake.url()]}
        )
        assert resp.status_code == 202

    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_valid_files_and_urls_combined(self, mock_start, mock_process, client):
        """Enviar arquivos e URLs válidos juntos deve retornar 202."""
        mock_start.return_value = str(uuid.uuid4())
        resp = client.post(
            ENDPOINT,
            files=[_make_upload("a.png"), _make_upload("b.jpeg")],
            data={"images_urls": [fake.url()]},
        )
        assert resp.status_code == 202

    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_response_message_is_present(self, mock_start, mock_process, client):
        """A resposta de sucesso deve conter uma mensagem informativa."""
        mock_start.return_value = str(uuid.uuid4())
        resp = client.post(ENDPOINT, files=[_make_upload("img.png")])
        assert resp.status_code == 202
        body = resp.json()
        assert "stream_url" in body["message"].lower()

    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_start_job_called_with_url_list(self, mock_start, mock_process, client):
        """start_job deve receber a lista de URLs validadas."""
        mock_start.return_value = str(uuid.uuid4())
        url = fake.url()
        client.post(ENDPOINT, data={"images_urls": [url]})
        _, kwargs = mock_start.call_args
        # Segundo argumento posicional é a lista de URLs
        called_urls = mock_start.call_args[0][1]
        assert url in called_urls

    @patch("app.routers.gc_image_import.process_image_job", new_callable=AsyncMock)
    @patch("app.routers.gc_image_import.start_job", new_callable=AsyncMock)
    def test_process_image_job_called_in_background(self, mock_start, mock_process, client):
        """process_image_job deve ser disparado após criação do job."""
        job_id = str(uuid.uuid4())
        mock_start.return_value = job_id
        client.post(ENDPOINT, files=[_make_upload("foto.png")])
        mock_process.assert_called_once()
        # Primeiro argumento é o job_id
        assert mock_process.call_args[0][0] == job_id
