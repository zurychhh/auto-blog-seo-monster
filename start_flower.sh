#!/bin/bash

# Start Flower - Celery Monitoring Web UI
# Access at: http://localhost:5555

echo "Starting Flower - Celery Monitoring..."
echo "Web UI will be available at: http://localhost:5555"
echo ""

source venv/bin/activate

celery -A app.celery_app flower \
  --port=5555 \
  --broker=redis://localhost:6379/0
