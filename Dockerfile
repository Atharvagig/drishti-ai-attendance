# Drishti AI — Production Container Image
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    FLASK_ENV=production

# Install system dependencies for dlib compilation, BLAS acceleration, and OpenCV runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    liblapack-dev \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Upgrade build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install dependencies (utilizes Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Expose default port (overridden at runtime by host PORT environment variable)
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=45s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/api/health || exit 1

# Production startup using gunicorn with eventlet worker
CMD ["sh", "-c", "gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:${PORT:-5000} --chdir backend app_flask:app"]
