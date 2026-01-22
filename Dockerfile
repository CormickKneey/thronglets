# Multi-stage build for Thronglets ServiceBus with Frontend
FROM python:3.12-slim AS backend

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy Python dependency files
COPY pyproject.toml uv.lock README.md ./

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy Python source code
COPY thronglets/ ./thronglets/
COPY main.py ./

# Frontend build stage
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source code
COPY frontend/ ./

# Build frontend
RUN npm run build

# Final stage - combine backend and frontend
FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy Python dependencies and source
COPY --from=backend /app/pyproject.toml /app/uv.lock /app/README.md ./
COPY --from=backend /app/thronglets/ ./thronglets/
COPY --from=backend /app/main.py ./

# Copy built frontend files to the expected location
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist/

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application (Python backend serves both API and frontend)
CMD ["uv", "run", "python", "main.py"]
