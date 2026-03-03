FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY openapi/ ./openapi/

# Expose port
EXPOSE 8000

# Set environment variables
ENV FLASK_APP=app.main
ENV PYTHONUNBUFFERED=1

# Run the application
CMD ["python3", "-m", "flask", "run", "--host", "0.0.0.0", "--port", "8000"]