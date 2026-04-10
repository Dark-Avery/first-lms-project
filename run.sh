#!/bin/bash
set -euo pipefail

if [ -d "${PWD}/.venv/bin" ]; then
  export PATH="${PWD}/.venv/bin:${PATH}"
fi

if [ -z "${CELERY_BROKER_URL:-}" ]; then
  echo "CELERY_BROKER_URL must be set" >&2
  exit 1
fi

python manage.py migrate

python -m celery -A config worker -l INFO &
CELERY_WORKER_PID=$!

python -m celery -A config beat -l INFO &
CELERY_BEAT_PID=$!

gunicorn config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers=1 \
  --threads=4 \
  --worker-tmp-dir="${GUNICORN_WORKER_TMP_DIR:-/tmp}" \
  --timeout=120 &
GUNICORN_PID=$!

cleanup() {
  kill "$CELERY_WORKER_PID" "$CELERY_BEAT_PID" "$GUNICORN_PID" 2>/dev/null || true
}

trap cleanup EXIT SIGINT SIGTERM

wait -n "$CELERY_WORKER_PID" "$CELERY_BEAT_PID" "$GUNICORN_PID"
EXIT_CODE=$?

kill "$CELERY_WORKER_PID" "$CELERY_BEAT_PID" "$GUNICORN_PID" 2>/dev/null || true
wait "$CELERY_WORKER_PID" "$CELERY_BEAT_PID" "$GUNICORN_PID" 2>/dev/null || true

exit "$EXIT_CODE"
