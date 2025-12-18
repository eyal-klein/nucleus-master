FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy shared modules first
COPY backend/shared /app/shared

# Copy service requirements and install
COPY backend/services/proactive-engagement-engine/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY backend/services/proactive-engagement-engine/main.py .

# Set Python path for shared modules
ENV PYTHONPATH=/app:/app/shared

# Run the service
CMD ["python", "main.py"]
