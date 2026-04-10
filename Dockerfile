# Build frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Resolve Python deps natively on the build host (no QEMU) to avoid uv
# segfaults when cross-building linux/amd64 from an arm64 host.
FROM --platform=$BUILDPLATFORM python:3.12-slim AS deps
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY backend/pyproject.toml backend/uv.lock* ./
RUN uv export --frozen --no-dev --format requirements-txt > /tmp/requirements.txt

# Production image
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv so `uv run` works at container startup (runs natively on
# Azure/Cloud Run and via Rosetta on Docker Desktop). Don't execute uv
# during the build — it segfaults under QEMU cross-build emulation.
RUN pip install --no-cache-dir uv

# Install locked Python dependencies (resolved in the deps stage) with pip,
# not uv, because uv crashes under QEMU. semgrep ships as a regular Python
# dependency in pyproject.toml, so no separate `uv tool install` is needed.
COPY --from=deps /tmp/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy backend source
COPY backend/ ./

# Copy Next.js static export (from 'out' directory)
COPY --from=frontend-build /app/out ./static

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port for Cloud Run / Azure Container Instances
EXPOSE 8000


# Start the FastAPI server
CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]