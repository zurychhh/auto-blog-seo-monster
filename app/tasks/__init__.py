"""
Celery tasks package.

Exports all task modules for easy imports.
"""

from app.tasks.post_tasks import (
    generate_post_for_agent,
    process_agent_schedules,
)

from app.tasks.publishing_tasks import (
    publish_post,
    publish_scheduled_posts,
    retry_failed_publications,
)

from app.tasks.source_tasks import (
    monitor_rss_feed,
    monitor_all_rss_feeds,
    test_source_connection,
)

from app.tasks.maintenance_tasks import (
    cleanup_old_results,
    health_check,
)

__all__ = [
    # Post tasks
    "generate_post_for_agent",
    "process_agent_schedules",
    # Publishing tasks
    "publish_post",
    "publish_scheduled_posts",
    "retry_failed_publications",
    # Source tasks
    "monitor_rss_feed",
    "monitor_all_rss_feeds",
    "test_source_connection",
    # Maintenance tasks
    "cleanup_old_results",
    "health_check",
]
