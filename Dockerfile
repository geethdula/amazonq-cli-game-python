FROM public.ecr.aws/docker/library/python:3.9-slim

# Install system dependencies for pygame (minimal headless setup)
RUN apt-get update && apt-get install -y \
    libsdl2-2.0-0 \
    libfreetype6 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create assets directory
RUN mkdir -p /app/assets

# Copy application code and assets
COPY app.py .
COPY assets/ ./assets/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8080
ENV SDL_VIDEODRIVER=dummy
ENV SDL_AUDIODRIVER=dummy
ENV PYGAME_HIDE_SUPPORT_PROMPT=1

# Expose the application port
EXPOSE 8080

# Use gunicorn as the production web server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app", "--workers", "2", "--threads", "4", "--timeout", "60"]
