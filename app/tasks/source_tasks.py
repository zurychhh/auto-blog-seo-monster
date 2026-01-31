"""
Source monitoring tasks.

Handles RSS feed monitoring and automatic content discovery.
"""

import logging
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.source import Source
from app.models.agent import Agent
from app.adapters import create_source_adapter
from app.tasks.post_tasks import generate_post_for_agent

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
    name="app.tasks.source_tasks.monitor_rss_feed",
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def monitor_rss_feed(self, source_id: str, auto_generate: bool = False):
    """
    Monitor a specific RSS feed for new content.

    Args:
        source_id: Source UUID
        auto_generate: If True, automatically trigger post generation for new items

    Returns:
        dict with monitoring results
    """
    import asyncio

    async def _monitor():
        db = await self.get_db()
        try:
            # Get source
            result = await db.execute(
                select(Source).where(Source.id == UUID(source_id))
            )
            source = result.scalar_one_or_none()

            if not source:
                logger.error(f"Source {source_id} not found")
                return {"success": False, "error": "Source not found"}

            # Fetch content using adapter
            adapter = create_source_adapter(source.type, source.config)
            contents = await adapter.fetch()

            if not contents:
                logger.info(f"No content found in source {source_id}")
                return {
                    "success": True,
                    "source_id": source_id,
                    "items_found": 0,
                    "posts_triggered": 0,
                }

            logger.info(f"Found {len(contents)} items in source {source_id}")

            posts_triggered = 0

            # If auto_generate is enabled, trigger post generation for new items
            if auto_generate:
                # Get agent
                agent_result = await db.execute(
                    select(Agent).where(Agent.id == source.agent_id)
                )
                agent = agent_result.scalar_one_or_none()

                if agent and agent.is_active:
                    # Trigger generation for first N items (limit to avoid overwhelming)
                    max_auto_generate = 3
                    for content in contents[:max_auto_generate]:
                        try:
                            # Use content title as topic and extract keyword
                            topic = content.title
                            # Simple keyword extraction: take first 2-3 words from title
                            keyword = " ".join(content.title.split()[:2])

                            # Trigger async post generation
                            generate_post_for_agent.delay(
                                str(agent.id),
                                topic=topic,
                                keyword=keyword
                            )
                            posts_triggered += 1
                            logger.info(f"Triggered post generation for: {topic}")

                        except Exception as e:
                            logger.error(f"Error triggering post generation: {e}")
                            continue

            return {
                "success": True,
                "source_id": source_id,
                "source_name": source.name,
                "items_found": len(contents),
                "posts_triggered": posts_triggered,
                "items": [
                    {
                        "title": content.title,
                        "url": content.url,
                        "published_at": content.published_at,
                    }
                    for content in contents[:5]  # Return first 5
                ],
            }

        except Exception as e:
            logger.error(f"Error monitoring RSS feed {source_id}: {e}", exc_info=True)
            raise
        finally:
            await self.close_db()

    return asyncio.run(_monitor())


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.source_tasks.monitor_all_rss_feeds",
)
def monitor_all_rss_feeds(self, auto_generate: bool = False):
    """
    Monitor all RSS feeds for new content.

    Called every 30 minutes by Celery Beat.

    Args:
        auto_generate: If True, automatically trigger post generation for new items

    Returns:
        dict with monitoring results for all feeds
    """
    import asyncio

    async def _monitor_all():
        db = await self.get_db()
        try:
            # Get all RSS sources
            result = await db.execute(
                select(Source).where(Source.type == "rss")
            )
            sources = result.scalars().all()

            if not sources:
                logger.info("No RSS sources found")
                return {
                    "success": True,
                    "sources_checked": 0,
                    "total_items": 0,
                }

            monitored_count = 0
            total_items = 0
            total_posts_triggered = 0

            for source in sources:
                try:
                    # Trigger async monitoring for each source
                    monitor_rss_feed.delay(str(source.id), auto_generate=auto_generate)
                    monitored_count += 1
                    logger.info(f"Triggered monitoring for source {source.id} ({source.name})")

                except Exception as e:
                    logger.error(f"Error triggering monitoring for source {source.id}: {e}")
                    continue

            logger.info(
                f"Monitored {monitored_count} RSS sources, "
                f"found {total_items} items, "
                f"triggered {total_posts_triggered} posts"
            )

            return {
                "success": True,
                "sources_checked": monitored_count,
                "total_sources": len(sources),
            }

        except Exception as e:
            logger.error(f"Error monitoring all RSS feeds: {e}", exc_info=True)
            raise
        finally:
            await self.close_db()

    return asyncio.run(_monitor_all())


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.source_tasks.test_source_connection",
)
def test_source_connection(self, source_id: str):
    """
    Test connection to a source.

    Args:
        source_id: Source UUID

    Returns:
        dict with test results
    """
    import asyncio

    async def _test():
        db = await self.get_db()
        try:
            # Get source
            result = await db.execute(
                select(Source).where(Source.id == UUID(source_id))
            )
            source = result.scalar_one_or_none()

            if not source:
                return {"success": False, "error": "Source not found"}

            # Test connection using adapter
            adapter = create_source_adapter(source.type, source.config)
            result = await adapter.test_connection()

            logger.info(f"Tested source {source_id}: {result['success']}")

            return {
                "success": True,
                "source_id": source_id,
                "test_result": result,
            }

        except Exception as e:
            logger.error(f"Error testing source {source_id}: {e}", exc_info=True)
            return {
                "success": False,
                "source_id": source_id,
                "error": str(e),
            }
        finally:
            await self.close_db()

    return asyncio.run(_test())
