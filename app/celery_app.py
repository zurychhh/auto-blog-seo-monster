"""
Celery application configuration.

Handles asynchronous task execution and scheduled jobs.
"""

from celery import Celery
from celery.schedules import crontab
from app.config import settings

# Create Celery application
celery_app = Celery(
    "auto_blog",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.post_tasks",
        "app.tasks.publishing_tasks",
        "app.tasks.source_tasks",
        "app.tasks.auto_publish_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max task time
    task_soft_time_limit=3000,  # 50 min soft limit

    # Results
    result_expires=86400,  # Results expire after 24 hours
    result_extended=True,

    # Retries
    task_acks_late=True,
    task_reject_on_worker_lost=True,

    # Worker
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Beat schedule (cron jobs)
    beat_schedule={
        # Check for scheduled posts every minute
        "check-scheduled-posts": {
            "task": "app.tasks.publishing_tasks.publish_scheduled_posts",
            "schedule": crontab(minute="*/1"),  # Every minute
        },
        # Monitor RSS feeds every 30 minutes
        "monitor-rss-feeds": {
            "task": "app.tasks.source_tasks.monitor_all_rss_feeds",
            "schedule": crontab(minute="*/30"),  # Every 30 minutes
        },
        # Process pending agent generations every 5 minutes
        "process-agent-schedules": {
            "task": "app.tasks.post_tasks.process_agent_schedules",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        },
        # Cleanup old task results daily at 3 AM
        "cleanup-task-results": {
            "task": "app.tasks.maintenance_tasks.cleanup_old_results",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        },
        # Process auto-publish schedules every hour
        "process-auto-publish-schedules": {
            "task": "app.tasks.auto_publish_tasks.process_auto_publish_schedules",
            "schedule": crontab(minute=0),  # Every hour at :00
        },
    },
)

# Task routes (optional - for queue-based task routing)
celery_app.conf.task_routes = {
    "app.tasks.post_tasks.*": {"queue": "generation"},
    "app.tasks.publishing_tasks.*": {"queue": "publishing"},
    "app.tasks.source_tasks.*": {"queue": "sources"},
    "app.tasks.maintenance_tasks.*": {"queue": "maintenance"},
    "app.tasks.auto_publish_tasks.*": {"queue": "generation"},
}
