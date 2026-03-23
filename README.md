# GC Finder API

API REST para localização e gerenciamento de Grupos de Crescimento (GCs) da Igreja Batista da Lagoinha, permitindo que qualquer pessoa encontre o GC mais próximo da sua casa pelo CEP.

## Sobre o projeto

O GC Finder API é o backend responsável por:

- Busca de GCs próximos por CEP, com cálculo de distância via coordenadas geográficas
- Exibição de GCs em mapa com latitude e longitude
- CRUD completo de GCs, líderes, encontros e mídias
- Autenticação JWT com refresh token rotativo
- Envio automatizado de interesse ao formulário oficial da Lagoinha Jundiaí via Google Forms
- Geocodificação automática de endereços ao cadastrar GCs (ViaCEP + Google Maps)

## Stack técnica

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.12 ou 3.13 (build padrão) |
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.x async + Alembic |
| Banco de dados | PostgreSQL 16 |
| Cache | Redis 7 |
| Autenticação | JWT com refresh token rotativo |
| Validação | Pydantic v2 |
| HTTP Client | httpx (async) |
| Testes | pytest + pytest-asyncio |
| Containerização | Docker + Docker Compose |
| Gerenciador de pacotes | Poetry |

## Serviços OCR

A importação de GCs por imagem suporta 2 serviços OCR, instaláveis de forma independente:

| Serviço | Grupo Poetry | Descrição |
|---|---|---|
| Tesseract | `ocr-tesseract` | OCR tradicional, leve e rápido. Requer binário `tesseract-ocr` no sistema |
| Google Document AI | `ocr-documentai` | Serviço gerenciado do Google Cloud. Requer projeto e processador configurados |

O serviço é escolhido por requisição via parâmetro `ocr_service` no endpoint `POST /api/v1/gcs/import/image`. Apenas serviços instalados e listados em `OCR_AVAILABLE_SERVICES` ficam disponíveis.

## Integrações externas

- **ViaCEP** — Busca de endereço a partir do CEP (API pública)
- **Google Maps Geocoding API** — Conversão de endereço em coordenadas lat/lng
- **Google Document AI** — Extração de texto de imagens via OCR na nuvem (opcional)
- **Google Forms** — Envio de interesse ao formulário oficial dos responsáveis de GCs

## Endpoints

### Públicos (sem autenticação)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/health` | Status da API e do banco |
| GET | `/api/v1/public/gcs/map` | GCs ativos com coordenadas para o mapa |
| GET | `/api/v1/public/gcs/nearby?zip_code=13214000` | GCs próximos por CEP |
| POST | `/api/v1/public/interest` | Registra interesse e envia ao Google Forms |
| GET | `/api/v1/leaders` | Lista líderes ativos |
| GET | `/api/v1/leaders/{id}` | Detalhe do líder |
| GET | `/api/v1/gcs` | Lista GCs ativos (paginado) |
| GET | `/api/v1/gcs/{id}` | Detalhe do GC com líderes, encontros e mídias |
| GET | `/api/v1/gcs/{gc_id}/meetings` | Encontros do GC |
| GET | `/api/v1/gcs/{gc_id}/medias` | Mídias do GC |

### Autenticação

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/auth/login` | Login com email/senha |
| POST | `/api/v1/auth/refresh` | Renova access token |
| POST | `/api/v1/auth/logout` | Revoga refresh token |
| GET | `/api/v1/auth/me` | Dados do usuário autenticado |

### Protegidos (requer autenticação)

CRUD completo para GCs, líderes, encontros e mídias via `POST`, `PUT` e `DELETE` nos prefixos `/api/v1/gcs`, `/api/v1/leaders`, `/api/v1/gcs/{gc_id}/meetings` e `/api/v1/gcs/{gc_id}/medias`.

### Importação de GC por imagem (requer autenticação)

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/v1/gcs/import/image` | Envia imagens para extração OCR (retorna job_id) |
| GET | `/api/v1/gcs/import/jobs/{job_id}/stream` | Acompanha progresso via SSE |
| POST | `/api/v1/gcs/import/save` | Salva os dados extraídos como GC no banco |

### Admin (requer role `admin`)

CRUD de usuários em `/api/v1/users`.

## Documentação interativa

Com a API rodando, acesse:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## Estrutura do projeto

```
app/
├── main.py              # Entrypoint FastAPI, registro de routers, CORS
├── config.py            # Settings via pydantic-settings
├── database.py          # Engine e sessão async do SQLAlchemy
├── logging_config.py    # Configuração centralizada de logging
├── dependencies.py      # Dependências compartilhadas (get_db, auth)
├── models/              # Modelos SQLAlchemy
├── schemas/             # Schemas Pydantic (request/response)
├── routers/             # Handlers dos endpoints
├── services/            # Regras de negócio
├── repositories/        # Acesso a dados
└── utils/               # Utilitários (JWT, bcrypt, validação de CEP)

seeds/                   # Scripts de seed idempotentes
alembic/                 # Migrações de banco de dados
```

## Pré-requisitos

- [Docker](https://docs.docker.com/get-docker/) e [Docker Compose](https://docs.docker.com/compose/install/)
- [Poetry](https://python-poetry.org/docs/#installation) (para desenvolvimento local)
- [Python 3.12 ou 3.13](https://www.python.org/downloads/) (para desenvolvimento local)

> Observação: o projeto não suporta Python free-threaded (`3.14t`) no momento, devido a incompatibilidades de extensões nativas usadas pela stack async.
- Chave da [Google Maps Geocoding API](https://developers.google.com/maps/documentation/geocoding/start) (para geocodificação)

## Como começar

Consulte o arquivo [SETUP.md](SETUP.md) para instruções detalhadas de configuração e execução.

## Licença

Este projeto é open source. Consulte o arquivo [LICENSE](LICENSE) para detalhes.
