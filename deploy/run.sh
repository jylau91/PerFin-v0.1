#!/usr/bin/env bash
# Launch PerFin bound to the Mac's tailnet IP (or 127.0.0.1 if TAILSCALE_BIND=0).
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${TAILSCALE_BIND:-1}" == "1" ]] && command -v tailscale >/dev/null 2>&1; then
  HOST="$(tailscale ip -4 | head -n1)"
  HOST="${HOST:-127.0.0.1}"
else
  HOST="127.0.0.1"
fi
PORT="${PERFIN_PORT:-8787}"

exec uv run uvicorn app.main:app --host "$HOST" --port "$PORT"
