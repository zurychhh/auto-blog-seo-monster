"""
Maintenance tasks.

Handles cleanup and maintenance operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from celery import Task
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""

    _db: Optional[AsyncSession] = None

    async def get_db(self) -> AsyncSession:
        """Get async database session."""
        if self._db is None:
            self._db = AsyncSessionLocal()
        return self._db

    async def close_db(self):
        """Close database session."""
        if self._db:
            await self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.maintenance_tasks.cleanup_old_results",
)
def cleanup_old_results(self, days_old: int = 7):
    """
    Clean up old Celery task results from Redis.

    Called daily at 3 AM by Celery Beat.

    Args:
        days_old: Remove results older than this many days

    Returns:
        dict with cleanup stats
    """
    import asyncio
    from celery.result import AsyncResult

    async def _cleanup():
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Note: Celery automatically expires results based on result_expires config
            # This task is more of a placeholder for custom cleanup if needed

            logger.info(f"Cleanup old task results older than {days_old} days")

            # Custom cleanup logic can be added here
            # For example: cleaning up specific task types, logging, etc.

            return {
                "success": True,
                "cutoff_date": cutoff_date.isoformat(),
                "message": "Cleanup completed (handled by Celery auto-expiry)",
            }

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            raise

    return asyncio.run(_cleanup())


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.maintenance_tasks.health_check",
)
def health_check(self):
    """
    Celery health check task.

    Can be called to verify Celery workers are running.

    Returns:
        dict with health status
    """
    import asyncio

    async def _check():
        db = await self.get_db()
        try:
            # Test database connection
            await db.execute("SELECT 1")

            logger.info("Health check passed")

            return {
                "success": True,
                "timestamp": datetime.utcnow().isoformat(),
                "worker": self.request.hostname,
                "database": "connected",
            }

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        finally:
            await self.close_db()

    return asyncio.run(_check())
