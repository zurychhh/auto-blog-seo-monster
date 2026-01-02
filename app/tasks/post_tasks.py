"""
Post generation tasks.

Handles automated post generation based on agent schedules and triggers.
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
from app.models.agent import Agent
from app.models.post import Post
from app.models.source import Source
from app.ai.post_generator import get_post_generator
from app.services.seo_service import get_seo_service
from app.services.usage_service import get_usage_service
from app.ai.token_counter import get_token_counter
from app.adapters import create_source_adapter
from croniter import croniter

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
    name="app.tasks.post_tasks.generate_post_for_agent",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=3,
)
def generate_post_for_agent(self, agent_id: str, topic: Optional[str] = None, keyword: Optional[str] = None):
    """
    Generate a blog post for a specific agent.

    Args:
        agent_id: Agent UUID
        topic: Optional topic override
        keyword: Optional keyword override

    Returns:
        dict with post_id and status
    """
    import asyncio

    async def _generate():
        db = await self.get_db()
        try:
            # Get agent
            result = await db.execute(
                select(Agent).where(Agent.id == UUID(agent_id))
            )
            agent = result.scalar_one_or_none()

            if not agent or not agent.is_active:
                logger.warning(f"Agent {agent_id} not found or inactive")
                return {"success": False, "error": "Agent not found or inactive"}

            # Check tenant quotas
            usage_service = get_usage_service()
            quota_status = await usage_service.check_tenant_quota(
                db=db,
                tenant_id=agent.tenant_id,
                tokens_needed=3000,
                posts_needed=1,
            )

            if not quota_status["tokens_available"] or not quota_status["posts_available"]:
                logger.warning(f"Quota exceeded for tenant {agent.tenant_id}")
                return {"success": False, "error": "Quota exceeded"}

            # Fetch content from sources if available
            sources_content = await _fetch_sources_content(db, agent.id)

            # Generate post
            post_generator = get_post_generator()
            seo_service = get_seo_service()
            token_counter = get_token_counter()

            # Use provided topic/keyword or agent's expertise as fallback
            post_topic = topic or f"Latest trends in {agent.expertise or 'technology'}"
            post_keyword = keyword or (agent.expertise or "technology")

            generation_result = await post_generator.generate_post(
                agent=agent,
                topic=post_topic,
                keyword=post_keyword,
                sources_content=sources_content,
            )

            # Calculate SEO metrics
            readability_score = seo_service.calculate_readability_score(
                generation_result["content"]
            )

            keyword_density = {}
            if generation_result["keywords"]:
                keyword_density = seo_service.calculate_keyword_density(
                    generation_result["content"],
                    generation_result["keywords"]
                )

            # Generate slug
            slug = seo_service.generate_slug(generation_result["title"])

            # Create post
            new_post = Post(
                agent_id=agent.id,
                title=generation_result["title"],
                content=generation_result["content"],
                meta_title=generation_result["meta_title"],
                meta_description=generation_result["meta_description"],
                keywords=generation_result["keywords"],
                slug=slug,
                status="draft",
                tokens_used=generation_result["tokens_used"],
                word_count=generation_result["word_count"],
                readability_score=readability_score,
                keyword_density=keyword_density,
            )

            db.add(new_post)
            await db.flush()

            # Estimate cost and log usage
            cost = token_counter.estimate_cost(
                input_tokens=generation_result["tokens_used"] // 2,
                output_tokens=generation_result["tokens_used"] // 2,
            )

            await usage_service.log_usage(
                db=db,
                tenant_id=agent.tenant_id,
                action_type="scheduled_post_generation",
                tokens_used=generation_result["tokens_used"],
                cost=cost,
                agent_id=agent.id,
                meta_data={
                    "post_id": str(new_post.id),
                    "task_id": self.request.id,
                    "scheduled": True,
                    "word_count": generation_result["word_count"],
                },
            )

            # Update tenant counters
            await usage_service.update_tenant_usage(
                db=db,
                tenant_id=agent.tenant_id,
                tokens_delta=generation_result["tokens_used"],
                posts_delta=1,
            )

            await db.commit()
            await db.refresh(new_post)

            logger.info(f"Generated post {new_post.id} for agent {agent_id}")

            return {
                "success": True,
                "post_id": str(new_post.id),
                "title": new_post.title,
                "word_count": new_post.word_count,
                "status": new_post.status,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Error generating post for agent {agent_id}: {e}", exc_info=True)
            raise
        finally:
            await self.close_db()

    return asyncio.run(_generate())


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.post_tasks.process_agent_schedules",
)
def process_agent_schedules(self):
    """
    Process all agents with cron schedules.

    Checks which agents should generate posts now based on their schedule_cron.
    Called every 5 minutes by Celery Beat.

    Returns:
        dict with number of agents processed and posts generated
    """
    import asyncio

    async def _process():
        db = await self.get_db()
        try:
            # Get all active agents with schedules
            result = await db.execute(
                select(Agent).where(
                    Agent.is_active == True,
                    Agent.schedule_cron.is_not(None)
                )
            )
            agents = result.scalars().all()

            now = datetime.utcnow()
            posts_triggered = 0

            for agent in agents:
                try:
                    # Check if agent should run now
                    cron = croniter(agent.schedule_cron, now)
                    prev_run = cron.get_prev(datetime)

                    # Check if it should have run in last 5 minutes
                    if (now - prev_run).total_seconds() < 300:  # 5 minutes
                        # Trigger post generation asynchronously
                        generate_post_for_agent.delay(str(agent.id))
                        posts_triggered += 1
                        logger.info(f"Triggered post generation for agent {agent.id} ({agent.name})")

                except Exception as e:
                    logger.error(f"Error processing schedule for agent {agent.id}: {e}")
                    continue

            logger.info(f"Processed {len(agents)} agents, triggered {posts_triggered} post generations")

            return {
                "success": True,
                "agents_checked": len(agents),
                "posts_triggered": posts_triggered,
            }

        except Exception as e:
            logger.error(f"Error processing agent schedules: {e}", exc_info=True)
            raise
        finally:
            await self.close_db()

    return asyncio.run(_process())


async def _fetch_sources_content(db: AsyncSession, agent_id: UUID) -> Optional[str]:
    """
    Fetch content from agent's configured sources.

    Args:
        db: Database session
        agent_id: Agent UUID

    Returns:
        Combined content string or None
    """
    try:
        # Get agent's sources
        result = await db.execute(
            select(Source).where(Source.agent_id == agent_id)
        )
        sources = result.scalars().all()

        if not sources:
            return None

        all_content = []

        for source in sources:
            try:
                # Create adapter and fetch content
                adapter = create_source_adapter(source.type, source.config)
                contents = await adapter.fetch()

                # Take first 3 items from each source
                for content in contents[:3]:
                    all_content.append(f"Title: {content.title}\nContent: {content.content[:500]}...")

            except Exception as e:
                logger.error(f"Error fetching from source {source.id}: {e}")
                continue

        if all_content:
            return "\n\n---\n\n".join(all_content)

        return None

    except Exception as e:
        logger.error(f"Error fetching sources content: {e}")
        return None
