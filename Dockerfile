# Use the official Python image
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd -m appuser

# Set the working directory
WORKDIR /app

# Install dependencies first to take advantage of layer caching
COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files into the container
COPY . .

# Environment
ENV PORT=8080 \
    FLASK_ENV=production \
    FLASK_DEBUG=0

# Run as non-root
USER appuser

# Expose port 8080 for Cloud Run
EXPOSE 8080

# Start Gunicorn; point at wsgi:app
CMD exec gunicorn --bind 0.0.0.0:${PORT} \
                  --workers ${WEB_CONCURRENCY:-2} \
                  --threads ${GUNICORN_THREADS:-4} \
                  --timeout ${GUNICORN_TIMEOUT:-60} \
                  --access-logfile - \
                  --error-logfile - \
                  wsgi:app
