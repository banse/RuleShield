FROM python:3.12-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python package
COPY pyproject.toml README.md LICENSE ./
COPY ruleshield/ ./ruleshield/
COPY rules/ ./rules/

RUN pip install --no-cache-dir .

# Create data directory
RUN mkdir -p /data/rules && cp -r rules/* /data/rules/

# Expose proxy port
EXPOSE 8337

# Environment variables
ENV RULESHIELD_PORT=8337
ENV RULESHIELD_RULES_DIR=/data/rules
ENV RULESHIELD_LOG_LEVEL=info

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8337/health || exit 1

# Run proxy
CMD ["ruleshield", "start"]
