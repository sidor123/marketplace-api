FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY openapi/ ./openapi/
COPY scripts/ ./scripts/

RUN chmod +x ./scripts/generate_schemas.sh && ./scripts/generate_schemas.sh

RUN touch generated/__init__.py

COPY app/ ./app/

EXPOSE 8000

ENV FLASK_APP=app.main
ENV PYTHONUNBUFFERED=1

CMD ["python3", "-m", "flask", "run", "--host", "0.0.0.0", "--port", "8000"]