# syntax=docker/dockerfile:1

############################
# Stage 1 — build wheels
############################
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /wheels

RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential libpq-dev \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# psycopg is only needed for the PostgreSQL deployment target; the repo's
# requirements.txt stays SQLite-only so local dev is unchanged.
RUN pip wheel --wheel-dir /wheels -r requirements.txt "psycopg[binary]~=3.2"

############################
# Stage 2 — runtime
############################
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && rm -rf /var/lib/apt/lists/* \
 && useradd --create-home --uid 10001 bhudrishti

WORKDIR /app

COPY --from=builder /wheels /wheels
COPY requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt "psycopg[binary]~=3.2" \
 && rm -rf /wheels

COPY app ./app
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Uploads and the SQLite fallback file both live under /data so a single
# volume survives container replacement.
RUN mkdir -p /data/uploads && chown -R bhudrishti:bhudrishti /app /data

ENV UPLOAD_DIR=/data/uploads \
    DATABASE_URL=sqlite:////data/bhudrishti.db \
    WEB_CONCURRENCY=2 \
    PORT=8000

USER bhudrishti
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
