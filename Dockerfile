# ==============================================================================
# MahaSetu RPA Ecosystem - Production Dockerfile
# Base: Official Microsoft Playwright Python container with Chromium pre-installed
# ==============================================================================

FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=5000 \
    HOST=0.0.0.0 \
    FLASK_ENV=production \
    PLAYWRIGHT_HEADLESS_DEFAULT=true \
    WSGI_THREADS=4

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Install playwright browser dependencies if not present
RUN playwright install chromium

# Copy application source
COPY . .

# Package the Chrome Extension on build so it is immediately downloadable
RUN python scripts/package_extension.py

# Create persistent storage directory
RUN mkdir -p /app/backend/data/recordings /app/backend/data/screenshots

# Volume mount for bot storage and recordings persistence
VOLUME ["/app/backend/data"]

# Expose web application port
EXPOSE 5000

# Health check against dynamic PORT
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:${PORT:-5000}/api/health || exit 1

# Start production WSGI server binding to dynamic Railway $PORT
CMD ["sh", "-c", "gunicorn --workers=2 --threads=4 --bind 0.0.0.0:${PORT:-5000} --timeout=120 wsgi:application"]
