# Use official Python image (3.13-slim is not yet available, using 3.12)
FROM python:3.12

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=api.py
ENV FLASK_ENV=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose the port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run with optimized settings to prevent deadlock
# Key changes:
# - worker-class sync (no threading with multiprocessing)
# - workers 2 (reduced to minimize memory)
# - max-requests 100 (recycle workers to prevent memory accumulation)
# - timeout 300 (5 minutes for crypto operations)
# - worker-tmp-dir /dev/shm (use shared memory to avoid disk I/O issues)
CMD ["gunicorn", \
    "--bind", "0.0.0.0:5000", \
    "--workers", "2", \
    "--worker-class", "sync", \
    "--threads", "1", \
    "--max-requests", "100", \
    "--max-requests-jitter", "20", \
    "--timeout", "300", \
    "--worker-tmp-dir", "/dev/shm", \
    "--graceful-timeout", "30", \
    "--keep-alive", "5", \
    "--log-level", "info", \
    "api:app"]
