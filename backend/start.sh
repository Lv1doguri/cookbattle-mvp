#!/usr/bin/env bash
# 요리왕 실행 (Mac/Linux): ./start.sh
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
source .venv/bin/activate
python -m pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
python -m app.seed
( sleep 3; (open http://localhost:8000 || xdg-open http://localhost:8000) >/dev/null 2>&1 ) &
python -m uvicorn app.main:app --port 8000
