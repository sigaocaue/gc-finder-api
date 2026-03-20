FROM python:3.13-slim

WORKDIR /app

# Instala dependências do sistema e o Poetry
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir poetry \
    && poetry config virtualenvs.create false

COPY . .
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
        poetry install --no-interaction --no-ansi --with dev,ocr; \
    else \
        poetry install --no-interaction --no-ansi --without dev --with ocr; \
    fi

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
