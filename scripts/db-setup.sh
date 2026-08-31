#!/usr/bin/env bash
# One-time (and after every migration) setup of the hosted database.
#
# Vercel functions are serverless: there is no entrypoint that can run
# `alembic upgrade head` the way backend/docker-entrypoint.sh does, and doing
# it at cold start would race across concurrent invocations. So schema changes
# are applied from here — a workstation or a CI job — against the managed
# Postgres instance.
#
#   DATABASE_URL='postgresql+psycopg2://…' ./scripts/db-setup.sh          # migrate
#   DATABASE_URL='postgresql+psycopg2://…' ./scripts/db-setup.sh --seed   # + roles/categories/admin
#
# Use the DIRECT (non-pooled) connection string here; pgbouncer in transaction
# mode cannot run the DDL and advisory locks Alembic needs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/backend"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "DATABASE_URL is not set. Pass the direct Postgres URL, e.g.:" >&2
    echo "  DATABASE_URL='postgresql+psycopg2://user:pass@host/db' $0" >&2
    exit 1
fi
export DATABASE_URL

PY=./.venv/bin/python
[ -x "$PY" ] || PY=python3

echo "→ Checking connectivity…"
"$PY" - <<'CHECK'
import os
from sqlalchemy import create_engine, text
url = os.environ["DATABASE_URL"]
with create_engine(url, pool_pre_ping=True).connect() as c:
    print("  connected:", c.execute(text("select version()")).scalar_one().split(",")[0])
CHECK

echo "→ Applying migrations…"
"$PY" -m alembic upgrade head

if [ "${1:-}" = "--seed" ]; then
    echo "→ Seeding baseline data (idempotent)…"
    "$PY" -m app.database.seed
fi

echo "✓ Database ready."
