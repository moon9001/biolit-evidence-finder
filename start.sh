#!/usr/bin/env bash
# BioLitEvidence Finder - Linux/macOS one-click starter.
# First run installs dependencies; subsequent runs just start the servers.

set -e

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "============================================"
echo "  BioLitEvidence Finder - starting..."
echo "============================================"

# --- Backend ---
cd "$HERE/backend"
if [ ! -d ".venv" ]; then
  echo "[setup] Creating Python virtualenv..."
  command -v python3 >/dev/null 2>&1 || { echo "Python 3.11+ is required."; exit 1; }
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
if [ ! -f ".env" ]; then
  echo "[setup] Copying .env.example to .env (edit this file to add API keys)"
  cp .env.example .env
fi

# Start backend in background
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/biolit-backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID (logs: /tmp/biolit-backend.log)"

# --- Frontend ---
cd "$HERE/frontend"
if [ ! -d "node_modules" ]; then
  echo "[setup] Installing frontend dependencies..."
  command -v npm >/dev/null 2>&1 || { echo "Node.js 18+ is required."; kill $BACKEND_PID 2>/dev/null; exit 1; }
  npm install
fi

echo ""
echo "============================================"
echo "  BioLitEvidence Finder ready."
echo "  Frontend: http://localhost:5173"
echo "  Backend:  http://localhost:8000/docs"
echo "  Stop with: kill $BACKEND_PID  &&  Ctrl+C in this terminal"
echo "============================================"
echo ""

# Frontend runs in foreground so Ctrl+C stops everything
trap "kill $BACKEND_PID 2>/dev/null" EXIT
npm run dev -- --host 0.0.0.0 --port 5173
