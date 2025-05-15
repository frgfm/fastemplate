FROM python:3.13-slim

WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"
# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy
# cf. https://github.com/astral-sh/uv/issues/8085#issuecomment-2438256688
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"

# Install curl
RUN apt-get -y update \
    && apt-get install -y --no-install-recommends curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.7.3 /uv /bin/uv

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# copy project
COPY alembic.ini /app/alembic.ini
COPY migrations /app/migrations
COPY app /app/app

# Entrypoint
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
EXPOSE 5050
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD ["curl", "http://localhost:5050/health", "--max-time", "3"]
CMD ["./entrypoint.sh"]
