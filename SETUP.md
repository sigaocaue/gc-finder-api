# Configuração e execução

Guia passo a passo para configurar e executar o GC Finder API.

## 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/gc-finder-api.git
cd gc-finder-api
```

## 2. Configurar variáveis de ambiente

Copie o arquivo de exemplo e edite com suas credenciais:

```bash
cp .env.example .env
```

Variáveis que devem ser alteradas antes de usar:

| Variável | Descrição |
|---|---|
| `APP_SECRET_KEY` | Chave secreta da aplicação |
| `DATABASE_URL` | URL de conexão com o PostgreSQL (deve coincidir com `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB`) |
| `POSTGRES_USER` | Usuário do PostgreSQL no Docker |
| `POSTGRES_PASSWORD` | Senha do PostgreSQL no Docker |
| `POSTGRES_DB` | Nome do banco de dados |
| `REDIS_URL` | URL de conexão com o Redis (deve coincidir com `REDIS_PASSWORD`) |
| `REDIS_PASSWORD` | Senha do Redis no Docker |
| `JWT_ACCESS_SECRET` | Chave para assinar tokens de acesso |
| `JWT_REFRESH_SECRET` | Chave para assinar tokens de refresh |
| `GOOGLE_MAPS_API_KEY` | Chave da API do Google Maps Geocoding |

> **Importante:** a `DATABASE_URL` e a `REDIS_URL` devem usar as mesmas credenciais definidas nas variáveis `POSTGRES_*` e `REDIS_*` respectivamente.

## 3. Subir os serviços com Docker Compose

```bash
docker-compose up -d
```

Isso inicia três serviços:

| Serviço | Porta | Descrição |
|---|---|---|
| `api` | 8000 | FastAPI com hot reload |
| `db` | 5432 | PostgreSQL 16 |
| `cache` | 6379 | Redis 7 |

Verifique se todos estão rodando:

```bash
docker-compose ps
```

## 4. Executar as migrações

Gere e aplique as migrações do banco de dados:

```bash
# Gerar migração inicial (se ainda não existir)
docker-compose exec api alembic revision --autogenerate -m "create_all_tables"

# Aplicar migrações
docker-compose exec api alembic upgrade head
```

## 5. Popular o banco com dados iniciais (seeds)

```bash
docker-compose exec api python -m seeds.run_seeds
```

Isso cria:
- 2 usuários (admin e editor)
- 5 líderes fictícios
- 5 GCs na região de Jundiaí/SP com endereços reais
- Encontros semanais para cada GC
- Mídias de exemplo

Os seeds são idempotentes — podem ser executados múltiplas vezes sem duplicar dados.

### Credenciais dos usuários de seed

| Email | Senha | Role |
|---|---|---|
| `admin@gcfinder.com` | `admin123` | admin |
| `editor@gcfinder.com` | `editor123` | editor |

## 6. Verificar se a API está funcionando

```bash
curl http://localhost:8000/health
```

Resposta esperada:

```json
{
  "data": { "status": "ok", "database": "ok" },
  "message": "Serviço operacional"
}
```

Acesse a documentação interativa:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Desenvolvimento local com Poetry

Para trabalhar no código com autocomplete e debug na IDE:

> Use Python 3.12 ou 3.13 (build padrão). Python free-threaded (`3.14t`) não é suportado neste projeto.

```bash
# Instalar dependências (inclui grupo dev)
poetry install

# Rodar comandos no ambiente virtual do Poetry
poetry run pytest -v
```

### Configurar o interpretador na IDE (PyCharm)

1. Descubra o caminho do virtualenv: `poetry env info --path`
2. Em **Settings > Project > Python Interpreter**, adicione um novo interpretador
3. Selecione **Poetry Environment > Existing environment**
4. Aponte para `<caminho>/bin/python`

---

## Comandos úteis

### Docker Compose

```bash
# Ver logs da API em tempo real
docker-compose logs -f api

# Reiniciar a API
docker-compose restart api

# Parar todos os serviços
docker-compose down

# Parar e remover volumes (apaga dados do banco)
docker-compose down -v
```

### Migrações (Alembic)

```bash
# Gerar nova migração após alterar models
docker-compose exec api alembic revision --autogenerate -m "descricao_da_alteracao"

# Aplicar todas as migrações pendentes
docker-compose exec api alembic upgrade head

# Reverter última migração
docker-compose exec api alembic downgrade -1

# Ver histórico de migrações
docker-compose exec api alembic history
```

### Testes

```bash
# Rodar testes via Poetry (local)
poetry run pytest -v

# Rodar testes via Docker
docker-compose exec api pytest -v
```

### Reconstruir o container da API

Após alterar dependências no `pyproject.toml`:

```bash
poetry lock
docker-compose build --no-cache api
docker-compose up -d
```

### Reinstalar dependências dentro do contêiner

Quando for preciso reinstalar todas as dependências (por exemplo, ao limpar caches ou ao mover o projeto para outro ambiente), use este comando dentro do contêiner da API para puxar os grupos `dev` e `ocr`:

```bash
docker-compose up -d api
docker-compose exec api poetry install --with dev,ocr
```
