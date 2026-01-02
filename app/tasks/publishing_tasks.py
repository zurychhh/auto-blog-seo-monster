"""
Publishing tasks.

Handles scheduled post publishing and republishing.
"""

import logging
from typing import Optional
from datetime import datetime
from uuid import UUID

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.celery_app import celery_app
from app.database import AsyncSessionLocal
from app.models.post import Post
from app.models.agent import Agent
from app.models.publisher import Publisher
from app.adapters import create_publisher_adapter

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
    name="app.tasks.publishing_tasks.publish_post",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def publish_post(self, post_id: str, publisher_id: Optional[str] = None):
    """
    Publish a post to configured publisher.

    Args:
        post_id: Post UUID
        publisher_id: Optional publisher UUID (uses agent default if not provided)

    Returns:
        dict with publication status
    """
    import asyncio

    async def _publish():
        db = await self.get_db()
        try:
            # Get post
            result = await db.execute(
                select(Post).where(Post.id == UUID(post_id))
            )
            post = result.scalar_one_or_none()

            if not post:
                logger.error(f"Post {post_id} not found")
                return {"success": False, "error": "Post not found"}

            # Get agent
            agent_result = await db.execute(
                select(Agent).where(Agent.id == post.agent_id)
            )
            agent = agent_result.scalar_one_or_none()

            if not agent:
                logger.error(f"Agent for post {post_id} not found")
                return {"success": False, "error": "Agent not found"}

            # Determine publisher
            pub_id = UUID(publisher_id) if publisher_id else agent.publisher_id

            if not pub_id:
                logger.error(f"No publisher configured for post {post_id}")
                return {"success": False, "error": "No publisher configured"}

            # Get publisher
            publisher_result = await db.execute(
                select(Publisher).where(Publisher.id == pub_id)
            )
            publisher = publisher_result.scalar_one_or_none()

            if not publisher:
                logger.error(f"Publisher {pub_id} not found")
                return {"success": False, "error": "Publisher not found"}

            # Verify publisher belongs to same agent
            if publisher.agent_id != agent.id:
                logger.error(f"Publisher {pub_id} doesn't belong to agent {agent.id}")
                return {"success": False, "error": "Publisher mismatch"}

            # Publish using adapter
            adapter = create_publisher_adapter(publisher.type, publisher.config)

            result = await adapter.publish(
                title=post.title,
                content=post.content,
                excerpt=post.excerpt,
                meta_title=post.meta_title,
                meta_description=post.meta_description,
                keywords=post.keywords,
                featured_image_url=post.og_image_url,
                status="publish",
            )

            if result.success:
                # Update post
                post.status = "published"
                post.published_url = result.published_url
                post.published_at = datetime.utcnow()
                post.publisher_id = publisher.id

                await db.commit()

                logger.info(f"Published post {post_id} to {publisher.type}: {result.published_url}")

                return {
                    "success": True,
                    "post_id": str(post.id),
                    "published_url": result.published_url,
                    "platform_post_id": result.published_id,
                    "publisher_type": publisher.type,
                }
            else:
                # Mark as failed
                post.status = "failed"
                await db.commit()

                logger.error(f"Failed to publish post {post_id}: {result.error}")

                return {
                    "success": False,
                    "error": result.error,
                    "post_id": str(post.id),
                }

        except Exception as e:
            await db.rollback()
            logger.error(f"Error publishing post {post_id}: {e}", exc_info=True)

            # Mark post as failed
            try:
                post_result = await db.execute(
                    select(Post).where(Post.id == UUID(post_id))
                )
                post = post_result.scalar_one_or_none()
                if post:
                    post.status = "failed"
                    await db.commit()
            except:
                pass

            raise
        finally:
            await self.close_db()

    return asyncio.run(_publish())


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.publishing_tasks.publish_scheduled_posts",
)
def publish_scheduled_posts(self):
    """
    Publish all posts scheduled for now.

    Called every minute by Celery Beat.
    Checks for posts with status='scheduled' and scheduled_at <= now.

    Returns:
        dict with number of posts published
    """
    import asyncio

    async def _publish_scheduled():
        db = await self.get_db()
        try:
            now = datetime.utcnow()

            # Get all scheduled posts due for publication
            result = await db.execute(
                select(Post).where(
                    Post.status == "scheduled",
                    Post.scheduled_at <= now
                )
            )
            posts = result.scalars().all()

            published_count = 0
            failed_count = 0

            for post in posts:
                try:
                    # Trigger async publication
                    publish_post.delay(str(post.id), str(post.publisher_id) if post.publisher_id else None)
                    published_count += 1
                    logger.info(f"Triggered publication for scheduled post {post.id}")

                except Exception as e:
                    logger.error(f"Error triggering publication for post {post.id}: {e}")
                    failed_count += 1

            logger.info(f"Processed {len(posts)} scheduled posts: {published_count} triggered, {failed_count} failed")

            return {
                "success": True,
                "posts_checked": len(posts),
                "posts_triggered": published_count,
                "posts_failed": failed_count,
            }

        except Exception as e:
            logger.error(f"Error processing scheduled posts: {e}", exc_info=True)
            raise
        finally:
            await self.close_db()

    return asyncio.run(_publish_scheduled())


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.publishing_tasks.retry_failed_publications",
)
def retry_failed_publications(self, max_retries: int = 3):
    """
    Retry publication of failed posts.

    Args:
        max_retries: Maximum number of retry attempts

    Returns:
        dict with retry results
    """
    import asyncio

    async def _retry():
        db = await self.get_db()
        try:
            # Get failed posts
            result = await db.execute(
                select(Post).where(Post.status == "failed")
            )
            failed_posts = result.scalars().all()

            retried_count = 0

            for post in failed_posts:
                try:
                    # Check if we should retry (could add retry counter to Post model)
                    publish_post.delay(str(post.id))
                    retried_count += 1
                    logger.info(f"Retrying publication for failed post {post.id}")

                except Exception as e:
                    logger.error(f"Error retrying publication for post {post.id}: {e}")

            logger.info(f"Retried {retried_count} of {len(failed_posts)} failed posts")

            return {
                "success": True,
                "failed_posts": len(failed_posts),
                "retried": retried_count,
            }

        except Exception as e:
            logger.error(f"Error retrying failed publications: {e}", exc_info=True)
            raise
        finally:
            await self.close_db()

    return asyncio.run(_retry())
