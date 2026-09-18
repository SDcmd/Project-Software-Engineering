#!/bin/bash
set -e
cd "$(dirname "$0")"

HELPERDEV_HOST="${HELPERDEV_HOST:-127.0.0.1}"
HELPERDEV_PORT="${HELPERDEV_PORT:-5001}"

if [ ! -x ".venv/bin/python" ]; then
  echo "Setting up HelperDev for the first time..."
  if command -v python3 >/dev/null 2>&1; then
    python3 -m venv .venv
  elif command -v python >/dev/null 2>&1; then
    python -m venv .venv
  else
    echo "Python 3 is required. Install Python 3 and run this file again."
    read -r -p "Press Enter to close..."
    exit 1
  fi
fi

if ! .venv/bin/python -c "import fastapi, uvicorn, jinja2, itsdangerous, multipart" >/dev/null 2>&1; then
  echo "Installing HelperDev dependencies..."
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
fi

echo "Starting HelperDev at http://${HELPERDEV_HOST}:${HELPERDEV_PORT}"
echo "Press Control+C to stop HelperDev."
.venv/bin/python -m uvicorn HelperDev.app:app --host "$HELPERDEV_HOST" --port "$HELPERDEV_PORT"
