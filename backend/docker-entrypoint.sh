#!/bin/sh
# Waits for PostgreSQL, applies migrations, optionally seeds, then starts the API.
set -e

echo "[entrypoint] Waiting for the database…"
python - <<'PY'
import os, sys, time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL", "")
if not url:
    sys.exit("DATABASE_URL is not set")

for attempt in range(1, 61):
    try:
        create_engine(url, pool_pre_ping=True).connect().execute(text("SELECT 1"))
        print(f"[entrypoint] Database reachable after {attempt} attempt(s)")
        break
    except Exception as exc:
        if attempt == 60:
            sys.exit(f"[entrypoint] Database unreachable: {type(exc).__name__}")
        time.sleep(1)
PY

echo "[entrypoint] Applying migrations…"
alembic upgrade head

# RUN_SEED=true creates roles, categories and the bootstrap admin (idempotent).
if [ "${RUN_SEED:-false}" = "true" ]; then
    echo "[entrypoint] Seeding baseline data…"
    if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
        python -m app.database.seed --demo
    else
        python -m app.database.seed
    fi
fi

echo "[entrypoint] Starting: $*"
exec "$@"
