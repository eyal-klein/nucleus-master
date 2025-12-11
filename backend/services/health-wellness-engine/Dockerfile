FROM python:3.11-slim

WORKDIR /app

# Copy shared modules
COPY backend/shared /app/backend/shared

# Copy service files
COPY backend/services/health-wellness-engine /app/backend/services/health-wellness-engine

# Install dependencies
RUN pip install --no-cache-dir -r /app/backend/services/health-wellness-engine/requirements.txt

# Set working directory to service
WORKDIR /app/backend/services/health-wellness-engine

# Expose port
EXPOSE 8000

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
