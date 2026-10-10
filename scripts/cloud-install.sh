#!/usr/bin/env bash
set -euo pipefail
cd /workspace/netmap
export PIP_CACHE_DIR=/tmp/netmap-pip-cache
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pip check
QT_QPA_PLATFORM=offscreen XDG_CACHE_HOME=/tmp/netmap-cache .venv/bin/python -m pytest -q
