FROM python:3.11-slim

WORKDIR /app

# Copy shared modules
COPY backend/shared /app/backend/shared

# Copy service files
COPY backend/services/context-aware-scheduler /app/backend/services/context-aware-scheduler

# Install dependencies
RUN pip install --no-cache-dir -r /app/backend/services/context-aware-scheduler/requirements.txt

# Set working directory to service
WORKDIR /app/backend/services/context-aware-scheduler

# Expose port
EXPOSE 8000

# Run the service
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
