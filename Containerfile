# ─────────────────────────────────────────────
# sherpa — Containerfile
# Podman rootless, RHEL 10.1
# ─────────────────────────────────────────────

FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Dependencias del sistema (psycopg2 necesita libpq, Pillow necesita libjpeg)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Usuario no-root dentro del contenedor
RUN useradd --create-home --shell /bin/bash sherpa
WORKDIR /app

# Instalar dependencias primero (cache de capas)
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install psycopg2-binary gunicorn \
    && pip install -r requirements.txt

# Copiar el código fuente
COPY src/ .

# Directorios de runtime
RUN mkdir -p /app/staticfiles /app/media /app/run \
    && chown -R sherpa:sherpa /app

USER sherpa

EXPOSE 8000

# Collectstatic en build, luego arrancar gunicorn
CMD ["gunicorn", \
     "core.wsgi:application", \
     "--name", "sherpa", \
     "--workers", "3", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
