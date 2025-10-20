# Copyright 2025 Christian Boulet / Boulet Stratégies TI
# Licensed under the Apache License, Version 2.0

# ==============================================================================
# SCOUT MCP Server - Multi-stage Docker Build
# ==============================================================================
# This Dockerfile creates a production-ready container for SCOUT.
#
# Build:
#   docker build -t scout-mcp:latest .
#
# Run with Docker Compose (recommended):
#   docker-compose up -d
#
# Run standalone (requires external Redis):
#   docker run --env-file .env -p 3000:3000 scout-mcp:latest
# ==============================================================================

# ==============================================================================
# Stage 1: Builder
# ==============================================================================
FROM python:3.11-slim as builder

LABEL maintainer="Christian Boulet <christian@bouletstrategies.com>"
LABEL description="SCOUT - Strategic CTO Operations and Unified Tooling MCP Server"
LABEL version="0.1.0"

# Set working directory
WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files and source code needed for installation
COPY pyproject.toml ./
COPY README.md ./
COPY src/ ./src/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --user .

# ==============================================================================
# Stage 2: Runtime
# ==============================================================================
FROM python:3.11-slim

# Set metadata
LABEL maintainer="Christian Boulet <christian@bouletstrategies.com>"
LABEL description="SCOUT MCP Server - Production Runtime"
LABEL version="0.1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/home/scout/.local/bin:$PATH" \
    SCOUT_ENV=production

# Create non-root user
RUN groupadd -r scout && \
    useradd -r -g scout -d /home/scout -s /bin/bash scout && \
    mkdir -p /home/scout /app && \
    chown -R scout:scout /home/scout /app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder --chown=scout:scout /root/.local /home/scout/.local

# Copy application code
COPY --chown=scout:scout src/ ./src/
COPY --chown=scout:scout config/ ./config/
COPY --chown=scout:scout pyproject.toml ./
COPY --chown=scout:scout README.md ./
COPY --chown=scout:scout LICENSE ./

# Switch to non-root user
USER scout

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/app/src'); from scout.server import ScoutMCPServer; import asyncio; server = ScoutMCPServer(); asyncio.run(server.initialize()); exit(0)" || exit 1

# Expose port (if running as HTTP server via FastMCP)
# Note: MCP typically uses stdio, but port exposed for future HTTP support
EXPOSE 3000

# Default command
CMD ["python", "-m", "scout.main"]
