#!/usr/bin/env bash
# One-shot Vercel configuration: env vars -> schema -> deploy -> verify.
#
# Prerequisites you must do yourself (they need a browser / your accounts):
#   1. vercel login          - authenticate the CLI
#   2. vercel link           - link this folder to the mf-ar-workstation project
#   3. Provision Postgres (Neon / Supabase / Vercel Postgres) and collect BOTH
#      connection strings, converted to the SQLAlchemy driver form:
#          postgresql+psycopg2://USER:PASS@HOST/DB?sslmode=require
#
# Then:
#   POOLED_URL='postgresql+psycopg2://…-pooler…'   \
#   DIRECT_URL='postgresql+psycopg2://…direct…'    \
#   ADMIN_PASSWORD='choose-a-strong-one'           \
#   ./scripts/vercel-setup.sh
#
# SECRET_KEY is generated here unless you export one.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DOMAIN="${DOMAIN:-https://mf-ar-workstation.vercel.app}"

for v in POOLED_URL DIRECT_URL ADMIN_PASSWORD; do
    if [ -z "${!v:-}" ]; then
        echo "Missing $v. See the header of this script for usage." >&2
        exit 1
    fi
done

command -v vercel >/dev/null || { echo "vercel CLI not installed: npm i -g vercel" >&2; exit 1; }
vercel whoami >/dev/null 2>&1 || { echo "Not logged in. Run: vercel login" >&2; exit 1; }
[ -f .vercel/project.json ] || { echo "Project not linked. Run: vercel link" >&2; exit 1; }

SECRET_KEY="${SECRET_KEY:-$(backend/.venv/bin/python -c 'import secrets;print(secrets.token_urlsafe(64))')}"

set_env() {
    # vercel env add refuses to overwrite, so drop any existing value first.
    local name="$1" value="$2"
    vercel env rm "$name" production --yes >/dev/null 2>&1 || true
    printf '%s' "$value" | vercel env add "$name" production >/dev/null
    echo "  set $name"
}

echo "→ Setting production environment variables…"
set_env DATABASE_URL          "$POOLED_URL"
set_env SECRET_KEY            "$SECRET_KEY"
set_env ENVIRONMENT           "production"
set_env COOKIE_SECURE         "true"
set_env COOKIE_SAMESITE       "lax"
set_env LOG_LEVEL             "INFO"
set_env FRONTEND_URL          "$DOMAIN"
set_env CORS_ORIGINS          "$DOMAIN"
set_env FIRST_ADMIN_EMPLOYEE_ID "ADMIN001"
set_env FIRST_ADMIN_NAME        "System Administrator"
set_env FIRST_ADMIN_EMAIL       "admin@example.com"
set_env FIRST_ADMIN_PASSWORD    "$ADMIN_PASSWORD"

echo "→ Applying schema and seeding the bootstrap admin…"
# The direct (non-pooled) URL: pgbouncer cannot run Alembic's DDL and locks.
DATABASE_URL="$DIRECT_URL" FIRST_ADMIN_PASSWORD="$ADMIN_PASSWORD" \
    ./scripts/db-setup.sh --seed

echo "→ Deploying to production…"
vercel --prod --yes

echo "→ Verifying…"
for _ in $(seq 1 20); do
    body="$(curl -fsS "$DOMAIN/api/health" 2>/dev/null || true)"
    case "$body" in
        *'"database":"ok"'*) echo "  $body"; echo "✓ API healthy. Sign in as ADMIN001."; exit 0 ;;
    esac
    sleep 3
done
echo "✗ /api/health did not report a healthy database. Check: vercel logs --prod" >&2
exit 1
