# syntax=docker/dockerfile:1.4
# ============================================================================
# Image Generation MCP Server - Multi-Stage Dockerfile
# FastMCP + FastAPI server for image generation/editing
# ============================================================================

# ============================================================================
# STAGE 1: Builder
# Install dependencies using pip, set up Python environment
# ============================================================================
FROM python:3.12-slim AS builder

LABEL maintainer="Jens Rehpöhler <jens@example.com>"
LABEL description="Builder stage for image.serv - installs dependencies"

# Set shell to bash for proper activation
SHELL ["/bin/bash", "-c"]

# Set environment variables for build stage
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# Install system dependencies required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    ca-certificates \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy project files needed for dependency resolution
COPY pyproject.toml README.md LICENSE.md ./
COPY uv.lock* ./

# Create virtual environment and install dependencies
# Use python -m venv to avoid uv complications, then use pip
RUN python -m venv /opt/venv && \
    pip install --upgrade pip setuptools wheel && \
    pip install -e .

# ============================================================================
# STAGE 2: Runtime
# Minimal production image with only runtime requirements
# ============================================================================
FROM python:3.12-slim AS runtime

# Build arguments for configuration
ARG APP_USER=app
ARG APP_UID=1000
ARG APP_GID=1000

# Set environment variables for runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PATH="/opt/venv/bin:${PATH}" \
    VIRTUAL_ENV=/opt/venv

# Install minimal runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user with explicit UID/GID
RUN groupadd -g ${APP_GID} ${APP_USER} && \
    useradd -d /home/${APP_USER} -s /sbin/nologin -u ${APP_UID} -g ${APP_GID} ${APP_USER} && \
    mkdir -p /home/${APP_USER} && \
    chown -R ${APP_USER}:${APP_USER} /home/${APP_USER}

# Copy virtual environment from builder stage
COPY --from=builder --chown=${APP_USER}:${APP_USER} /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application source code
COPY --chown=${APP_USER}:${APP_USER} server ./server
COPY --chown=${APP_USER}:${APP_USER} .env.example .env.example

# Create directories for runtime artifacts with proper permissions
RUN mkdir -p /app/images /app/logs && \
    chown -R ${APP_USER}:${APP_USER} /app/images /app/logs

# Switch to non-root user
USER ${APP_USER}

# Expose FastAPI port
EXPOSE 8000

# Health check - verify server is responding
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/docs || exit 1

# Default command: run the server
CMD ["python", "-m", "server.server"]
