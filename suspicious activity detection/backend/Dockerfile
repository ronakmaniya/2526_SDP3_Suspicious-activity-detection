# ===========================
# Django Backend Dockerfile
# ===========================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=surveillance_backend.settings

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create media directories
RUN mkdir -p media/live_recordings media/uploaded_videos \
    media/suspicious_clips media/processed_videos

# Collect static files
RUN python manage.py collectstatic --noinput 2>/dev/null || true

# Run migrations
RUN python manage.py migrate --noinput 2>/dev/null || true

EXPOSE 8000

# Run with gunicorn
CMD ["gunicorn", "surveillance_backend.wsgi:application", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--access-logfile", "-"]
