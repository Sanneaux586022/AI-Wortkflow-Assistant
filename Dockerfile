# 1. Usa l'immagine ufficiale di uv per prelevare il binario
FROM ghcr.io/astral-sh/uv:latest AS uv_bin

# 2. Immagine base Python
FROM python:3.12-slim

# Copia uv nel container
COPY --from=uv_bin /uv /uvx /bin/

# Imposta variabili d'ambiente per uv
# Evita di creare bytecode .pyc e forza l'uso dell'ambiente virtuale
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/venv

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copia i file di definizione (fondamentale copiare uv.lock!)
COPY pyproject.toml uv.lock ./


# Installiamo le dipendenze PRIMA di copiare il codice.
# Se il codice cambia , Docker salta questa fase pesante (Caching).
RUN uv sync --frozen --no-install-project --no-dev

# Ora copiamo il resto del progetto
COPY . .

# Installiamo il progetto stesso
RUN uv sync --frozen --no-dev

# Usiamo il percorso dell'ambiente virtuale creato da uv

ENV PATH="/venv/bin:$PATH"

# EXPOSE 10000

# CMD ["python", "main.py"]
# Avvio
CMD ["/bin/bash", "docker-entrypoint.sh"]
# CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "main:app"]