#!/bin/bash

# Start Celery Beat Scheduler
# Triggers scheduled/periodic tasks

echo "Starting Celery Beat Scheduler..."
echo "Scheduled tasks:"
echo "  - Check scheduled posts (every minute)"
echo "  - Monitor RSS feeds (every 30 minutes)"
echo "  - Process agent schedules (every 5 minutes)"
echo "  - Cleanup old results (daily at 3 AM)"
echo ""

source venv/bin/activate

celery -A app.celery_app beat \
  --loglevel=info \
  --scheduler celery.beat:PersistentScheduler
