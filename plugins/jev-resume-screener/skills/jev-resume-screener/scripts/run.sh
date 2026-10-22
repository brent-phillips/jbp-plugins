#!/usr/bin/env bash
# Launcher: finds Python 3.10+, keeps a private venv with pypdf and python-docx,
# then runs one of the screener scripts.  Usage: run.sh <script.py> [args...]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${JEV_SCREENER_HOME:-$HOME/.jev-screener}/venv"

if [ ! -x "$VENV/bin/python" ]; then
  PY=""
  for c in python3.13 python3.12 python3.11 python3.10 python3 \
           /opt/homebrew/bin/python3 /usr/local/bin/python3; do
    if command -v "$c" >/dev/null 2>&1 && \
       "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
      PY="$c"; break
    fi
  done
  if [ -z "$PY" ]; then
    echo "Python 3.10 or newer is required. Install it (e.g. 'brew install python@3.12') and retry." >&2
    exit 2
  fi
  echo "First run: setting up the screener's Python environment in $VENV" >&2
  "$PY" -m venv "$VENV"
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check pypdf python-docx
fi

script="$1"; shift
exec "$VENV/bin/python" -I "$HERE/$script" "$@"
