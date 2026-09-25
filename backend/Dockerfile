FROM python:3.14-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY --from=ghcr.io/astral-sh/uv:0.12.18 /uv /uvx /bin/
RUN uv sync --locked --no-dev --no-install-project
COPY app/ ./app/
COPY rds-ca-bundle.pem ./certs/rds-ca-bundle.pem
COPY alembic.ini ./
COPY migrations/ ./migrations/
USER 10001:10001
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
