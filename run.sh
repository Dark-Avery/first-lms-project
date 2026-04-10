#!/bin/bash
set -euo pipefail

if [ -d "${PWD}/.venv/bin" ]; then
  export PATH="${PWD}/.venv/bin:${PATH}"
fi

if [ -z "${CELERY_BROKER_URL:-}" ]; then
  if [ -n "${POSTGRES_CONNECTION_STRING:-}" ]; then
    CELERY_BROKER_URL="${POSTGRES_CONNECTION_STRING#postgres://}"
    CELERY_BROKER_URL="${CELERY_BROKER_URL#postgresql://}"
    export CELERY_BROKER_URL="sqla+postgresql+psycopg2://${CELERY_BROKER_URL}"
  elif [ -n "${POSTGRES_HOST:-}" ] && [ -n "${POSTGRES_PASSWORD:-}" ]; then
    POSTGRES_DATABASE="${POSTGRES_DATABASE_NAME:-${POSTGRES_DB:-}}"
    POSTGRES_USERNAME_VALUE="${POSTGRES_USERNAME:-${POSTGRES_USER:-}}"
    POSTGRES_PORT_VALUE="${POSTGRES_PORT:-5432}"

    export CELERY_BROKER_URL="sqla+postgresql+psycopg2://${POSTGRES_USERNAME_VALUE}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT_VALUE}/${POSTGRES_DATABASE}"
  fi
fi

PIDS=()

python manage.py migrate

gunicorn config.wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers=1 \
  --threads=4 \
  --worker-tmp-dir="${GUNICORN_WORKER_TMP_DIR:-/tmp}" \
  --timeout=120 &
GUNICORN_PID=$!
PIDS+=("$GUNICORN_PID")

if [ -n "${CELERY_BROKER_URL:-}" ]; then
  python -m celery -A config worker -l INFO &
  CELERY_WORKER_PID=$!
  PIDS+=("$CELERY_WORKER_PID")

  python -m celery -A config beat -l INFO &
  CELERY_BEAT_PID=$!
  PIDS+=("$CELERY_BEAT_PID")
else
  echo "CELERY_BROKER_URL is not set; starting web without worker and beat." >&2
fi

cleanup() {
  if [ "${#PIDS[@]}" -gt 0 ]; then
    kill "${PIDS[@]}" 2>/dev/null || true
  fi
}

trap cleanup EXIT SIGINT SIGTERM

wait -n "${PIDS[@]}"
EXIT_CODE=$?

if [ "${#PIDS[@]}" -gt 0 ]; then
  kill "${PIDS[@]}" 2>/dev/null || true
  wait "${PIDS[@]}" 2>/dev/null || true
fi

exit "$EXIT_CODE"
