#!/usr/bin/env bash
# Container start-up: wait for the database, create/seed it, then hand over to uvicorn.
set -euo pipefail

: "${DATABASE_URL:=sqlite:////data/bhudrishti.db}"
: "${SEED_ON_START:=true}"
: "${DB_WAIT_SECONDS:=60}"
: "${WEB_CONCURRENCY:=2}"

export DATABASE_URL

if [[ "${DATABASE_URL}" != sqlite* ]]; then
  echo "[entrypoint] waiting for database ..."
  python - "$DB_WAIT_SECONDS" <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

deadline = time.time() + float(sys.argv[1])
url = os.environ["DATABASE_URL"]
last = None
while time.time() < deadline:
    try:
        create_engine(url, pool_pre_ping=True).connect().execute(text("SELECT 1"))
        print("[entrypoint] database is up")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001 — any driver error means "not ready yet"
        last = exc
        time.sleep(1.5)
print(f"[entrypoint] database unreachable after timeout: {last}", file=sys.stderr)
sys.exit(1)
PY
fi

if [[ "${SEED_ON_START}" == "true" ]]; then
  # app.seed is idempotent: it creates the tables and skips if parcels exist.
  echo "[entrypoint] seeding database (idempotent) ..."
  python -m app.seed
fi

# SQLite cannot take concurrent writers, so force a single worker there.
if [[ "${DATABASE_URL}" == sqlite* ]]; then
  WEB_CONCURRENCY=1
fi

if [[ "${1:-}" == "uvicorn" && "${WEB_CONCURRENCY}" -gt 1 ]]; then
  set -- "$@" --workers "${WEB_CONCURRENCY}"
fi

echo "[entrypoint] starting: $*"
exec "$@"
