FROM node:24-bookworm-slim AS frontend-build
WORKDIR /build/frontend
RUN corepack enable
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm run build

FROM ubuntu:24.04 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:$PATH \
    SNSTUDIO_DATA_DIR=/data \
    SNSTUDIO_FRONTEND_DIST=/app/frontend/dist \
    SNSTUDIO_SUPERSNEC_ROOT=/opt/engines/supersnec \
    SNSTUDIO_SNEC_ROOT=/opt/engines/snec-1.01 \
    SNSTUDIO_STELLA_ROOT=/opt/engines/openstella
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      ca-certificates python3 python3-venv \
      libgfortran5 liblapack3 libblas3 openmpi-bin \
    && python3 -m venv /opt/venv \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY backend/ /app/backend/
RUN pip install --no-cache-dir /app/backend
COPY --from=frontend-build /build/frontend/dist /app/frontend/dist
EXPOSE 8787
CMD ["uvicorn", "snstudio.main:app", "--host", "0.0.0.0", "--port", "8787"]
