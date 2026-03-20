FROM python:3.13-slim

WORKDIR /app

# Instala dependências do sistema e o Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    tesseract-ocr \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

# Copia apenas os arquivos de dependências primeiro (cache de layer)
COPY pyproject.toml poetry.lock ./
ARG APP_ENV=development
RUN APP_ENV_LOWER=$(echo "$APP_ENV" | tr '[:upper:]' '[:lower:]') && \
    if [ "$APP_ENV_LOWER" = "production" ]; then \
        poetry install --no-interaction --no-ansi --without dev --with ocr --no-root; \
    else \
        poetry install --no-interaction --no-ansi --with dev,ocr --no-root; \
    fi

# Copia o restante do código
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
