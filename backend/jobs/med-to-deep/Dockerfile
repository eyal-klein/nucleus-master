FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy shared dependencies
COPY backend/shared /app/backend/shared

# Copy job code
COPY backend/jobs/med-to-deep /app/backend/jobs/med-to-deep

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/backend/shared/requirements.txt

# Set environment
ENV PYTHONUNBUFFERED=1

# Run the job
CMD ["python", "/app/backend/jobs/med-to-deep/main.py"]
