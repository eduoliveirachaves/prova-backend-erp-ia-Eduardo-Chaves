FROM python:3.14-slim AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /uvx /bin/
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --frozen --no-dev --no-editable

FROM builder AS test
ENV PATH="/app/.venv/bin:$PATH"
RUN uv sync --frozen --no-editable
COPY tests ./tests
CMD ["sh", "-c", "pytest -q && ruff check . && mypy src tests"]

FROM python:3.14-slim AS runtime
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/migrations /app/migrations
COPY --from=builder /app/alembic.ini /app/alembic.ini
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
CMD ["sh", "/app/docker/entrypoint.sh"]
