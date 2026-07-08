@'
FROM python:3.10-slim

# Create non-root user (UID 1000) — required by HF Spaces
RUN useradd -m -u 1000 user

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# === Redirect all caches to /tmp (only writable dir on HF Spaces) ===
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/tmp/hf_cache \
    TRANSFORMERS_CACHE=/tmp/hf_cache/transformers \
    XDG_CACHE_HOME=/tmp/cache \
    CHROMA_CACHE=/tmp/chroma_cache

# Create writable directories with proper permissions
RUN mkdir -p /tmp/hf_cache /tmp/chroma_db /tmp/cache /tmp/uploads /tmp/app_data && \
    chmod -R 777 /tmp

WORKDIR /app

# Copy and install requirements first (better caching)
COPY --chown=user ./requirements.txt requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user . /app

# Switch to non-root user
USER user

# Expose the port HF Spaces expects
EXPOSE 7860

# Run the FastAPI app — NOTE: api.main:app (not main:app)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
'@ | Out-File -Encoding utf8 Dockerfile