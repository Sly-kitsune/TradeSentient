FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker/ ./worker/

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
