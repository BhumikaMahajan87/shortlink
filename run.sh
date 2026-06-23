#!/usr/bin/env bash
# One-command runner for ShortLink.
# Creates a virtual environment, installs dependencies, and starts the server.
set -e
cd "$(dirname "$0")"

# Find a Python 3.11+ interpreter.
PY=""
for c in python3.12 python3.11 python3.13 python3; do
  if command -v "$c" >/dev/null 2>&1; then
    if "$c" -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
      PY="$c"; break
    fi
  fi
done

if [ -z "$PY" ]; then
  echo "Python 3.11+ not found. Install it with:  brew install python@3.12"
  exit 1
fi

if [ ! -d ".venv" ]; then
  echo "Setting up virtual environment with $PY ..."
  "$PY" -m venv .venv
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt
fi

echo ""
echo "ShortLink running!  Open these in your browser:"
echo "   Web UI:  http://localhost:8000"
echo "   API docs: http://localhost:8000/docs"
echo "   (press Ctrl+C to stop)"
echo ""
exec ./.venv/bin/uvicorn app.main:app --reload --port 8000
