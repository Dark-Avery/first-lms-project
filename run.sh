#!/bin/bash
set -euo pipefail

if [ -d "${PWD}/.venv/bin" ]; then
  export PATH="${PWD}/.venv/bin:${PATH}"
fi

python manage.py migrate

exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers=1 \
  --threads=4 \
  --worker-tmp-dir="${GUNICORN_WORKER_TMP_DIR:-/tmp}" \
  --timeout=120
