#!/usr/bin/env bash
# Start FastAPI (8000) + Next.js (3000). Requires: Python 3, Node/npm, and `npm install` in frontend/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export RECOMMENDER_CORS_ORIGINS="${RECOMMENDER_CORS_ORIGINS:-http://localhost:3000,http://127.0.0.1:3000}"

lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true

echo "Starting API on http://127.0.0.1:8000 ..."
(
  cd "$ROOT"
  RECOMMENDER_MAX_ROWS="${RECOMMENDER_MAX_ROWS:-8000}" \
  RECOMMENDER_API_HOST="${RECOMMENDER_API_HOST:-127.0.0.1}" \
  RECOMMENDER_API_PORT="${RECOMMENDER_API_PORT:-8000}" \
  python3 -m recommender.phase4.main
) &
API_PID=$!

sleep 3
if ! curl -sf "http://127.0.0.1:8000/health" >/dev/null; then
  echo "API did not become ready; check errors above."
  kill "$API_PID" 2>/dev/null || true
  exit 1
fi
echo "API OK (PID $API_PID)."

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found — install Node.js, then run:"
  echo "  cd \"$ROOT/frontend\" && npm install && npm run dev"
  echo "API is still running; press Ctrl+C or: kill $API_PID"
  wait "$API_PID"
  exit 0
fi

echo "Starting Next.js on http://localhost:3000 ..."
cd "$ROOT/frontend"
if [[ ! -d node_modules ]]; then
  npm install
fi
trap 'kill "$API_PID" 2>/dev/null; exit 0' INT TERM
npm run dev
kill "$API_PID" 2>/dev/null || true
