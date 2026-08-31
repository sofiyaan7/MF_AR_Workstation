#!/usr/bin/env bash
# Starts MF AR Workstation locally (backend + frontend) and keeps running
# until you press Ctrl+C, which stops both.
#
#   ./start.sh
#
# Ports can be overridden:  API_PORT=8020 WEB_PORT=5180 ./start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
API_PORT="${API_PORT:-8010}"
WEB_PORT="${WEB_PORT:-5173}"

if [ ! -f "$ROOT/backend/.env" ]; then
    echo "backend/.env is missing. Copy backend/.env.example and set SECRET_KEY." >&2
    exit 1
fi

port_busy() { (ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep -q ":$1 "; }
for port in "$API_PORT" "$WEB_PORT"; do
    if port_busy "$port"; then
        echo "Port $port is already in use. Free it, or re-run with a different port:" >&2
        echo "  API_PORT=8020 WEB_PORT=5180 ./start.sh" >&2
        exit 1
    fi
done

cleanup() {
    echo ""
    echo "Stopping…"
    [ -n "${API_PID:-}" ] && kill "$API_PID" 2>/dev/null || true
    [ -n "${WEB_PID:-}" ] && kill "$WEB_PID" 2>/dev/null || true
    wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "Starting API on http://127.0.0.1:$API_PORT …"
( cd "$ROOT/backend" && exec ./.venv/bin/uvicorn app.main:app \
      --host 127.0.0.1 --port "$API_PORT" --reload ) &
API_PID=$!

# Wait for the API before starting the web server, so the first page load
# does not race the backend.
for _ in $(seq 1 60); do
    curl -sf "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 && break
    sleep 0.5
done

echo "Starting web on http://localhost:$WEB_PORT …"
( cd "$ROOT/frontend" && VITE_API_PROXY="http://localhost:$API_PORT" \
      exec npx vite --port "$WEB_PORT" --host 127.0.0.1 ) &
WEB_PID=$!

cat <<BANNER

  ────────────────────────────────────────────────
   MF AR Workstation is running

   Portal    http://localhost:$WEB_PORT
   API docs  http://localhost:$API_PORT/docs

   Sign in with the Employee ID and password of an
   account created by an administrator.

   Press Ctrl+C to stop both services.
  ────────────────────────────────────────────────

BANNER

wait
