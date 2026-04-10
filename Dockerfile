FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

RUN addgroup --system --gid 1000 appuser && \
    adduser --system --uid 1000 --ingroup appuser --home /home/appuser appuser && \
    pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock manage.py run.sh ./
COPY config ./config
COPY health ./health
COPY events ./events
COPY tickets ./tickets
COPY sync ./sync
COPY integrations ./integrations

RUN uv sync --frozen --no-dev
RUN chown -R appuser:appuser /app

USER appuser

CMD ["bash", "./run.sh"]
