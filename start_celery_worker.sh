#!/bin/bash

# Start Celery Worker
# Processes asynchronous tasks from queues

echo "Starting Celery Worker..."
echo "Queues: generation, publishing, sources, maintenance"
echo ""

source venv/bin/activate

celery -A app.celery_app worker \
  --loglevel=info \
  --queues=generation,publishing,sources,maintenance \
  --concurrency=4 \
  --max-tasks-per-child=100
