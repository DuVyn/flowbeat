# syntax=docker/dockerfile:1.7

FROM python:3.13-slim AS base
WORKDIR /workspace/recsys

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    FLOWBEAT_WORKSPACE_ROOT=/workspace

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

CMD ["sh", "-lc", "${RECSYS_COMMAND:-sleep infinity}"]
