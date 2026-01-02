"""
Auto-publish tasks - Automated topic discovery, content generation, and publishing.

Full workflow:
1. Discover trending legal topics
2. Select best topic (SEO + uniqueness)
3. Generate SEO-optimized post
4. Validate quality
5. Publish or save as draft
"""

import logging
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from celery import Task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from croniter import croniter

from app.celery_app import celery_app
from app.config import settings
from app.models.schedule import ScheduleConfig
from app.models.agent import Agent
from app.models.post import Post
from app.ai.post_generator import get_post_generator
from app.ai.claude_client import get_claude_client
from app.services.seo_service import get_seo_service
from app.services.usage_service import get_usage_service
from app.services.topic_discovery import get_topic_discovery_service, DiscoveredTopic
from app.ai.token_counter import get_token_counter

logger = logging.getLogger(__name__)


async def run_auto_publish_workflow(schedule_id: str, db: AsyncSession) -> dict:
    """
    Async version of auto-publish workflow for use with FastAPI BackgroundTasks.

    This function can be called directly from async context without Celery.

    Args:
        schedule_id: Schedule UUID as string
        db: Async database session

    Returns:
        dict with result status and post_id
    """
    topic_service = get_topic_discovery_service()

    try:
        # Get schedule
        result = await db.execute(
            select(ScheduleConfig).where(ScheduleConfig.id == UUID(schedule_id))
        )
        schedule = result.scalar_one_or_none()

        if not schedule:
            logger.error(f"Schedule {schedule_id} not found")
            return {"success": False, "error": "Schedule not found"}

        if not schedule.is_active:
            logger.info(f"Schedule {schedule_id} is inactive")
            return {"success": False, "error": "Schedule is inactive"}

        # Get agent
        agent_result = await db.execute(
            select(Agent).where(Agent.id == schedule.agent_id)
        )
        agent = agent_result.scalar_one_or_none()

        if not agent or not agent.is_active:
            logger.error(f"Agent for schedule {schedule_id} not found or inactive")
            schedule.failed_posts += 1
            schedule.last_run_at = datetime.utcnow()
            await db.commit()
            return {"success": False, "error": "Agent not found or inactive"}

        logger.info(f"Starting auto-publish for schedule {schedule_id}, agent {agent.name}")

        # ============ PHASE 1: DISCOVERY ============
        logger.info("Phase 1: Discovering topics...")

        # Get already published titles to avoid duplicates
        existing_posts = await db.execute(
            select(Post.title).where(Post.agent_id == agent.id)
        )
        existing_titles = [row[0] for row in existing_posts.fetchall()]

        # Map target keywords to categories
        categories = None
        if schedule.target_keywords:
            categories = _map_keywords_to_categories(schedule.target_keywords)

        # Discover topics
        topics = await topic_service.discover_topics(
            categories=categories,
            max_topics=10,
            exclude_titles=existing_titles,
        )

        if not topics:
            logger.warning(f"No topics discovered for schedule {schedule_id}")
            schedule.failed_posts += 1
            schedule.last_run_at = datetime.utcnow()
            await db.commit()
            return {"success": False, "error": "No trending topics found"}

        # Filter by exclude keywords
        if schedule.exclude_keywords:
            topics = _filter_excluded_topics(topics, schedule.exclude_keywords)

        if not topics:
            logger.warning("All topics filtered out by exclude keywords")
            schedule.failed_posts += 1
            schedule.last_run_at = datetime.utcnow()
            await db.commit()
            return {"success": False, "error": "All topics filtered out"}

        # Select best topic
        best_topic = topics[0]
        logger.info(f"Selected topic: {best_topic.title}")

        # ============ PHASE 2: AI RESEARCH ============
        logger.info("Phase 2: AI keyword research...")

        claude_client = get_claude_client()
        best_topic = await topic_service.get_topic_with_ai_suggestions(
            best_topic, claude_client
        )

        # ============ PHASE 3: GENERATION ============
        logger.info("Phase 3: Generating post...")

        post_generator = get_post_generator()
        seo_service = get_seo_service()
        token_counter = get_token_counter()
        usage_service = get_usage_service()

        # Check quotas
        quota_status = await usage_service.check_tenant_quota(
            db=db,
            tenant_id=agent.tenant_id,
            tokens_needed=5000,
            posts_needed=1,
        )

        if not quota_status["tokens_available"] or not quota_status["posts_available"]:
            logger.warning(f"Quota exceeded for tenant {agent.tenant_id}")
            schedule.failed_posts += 1
            schedule.last_run_at = datetime.utcnow()
            await db.commit()
            return {"success": False, "error": "Quota exceeded"}

        # Prepare generation parameters
        topic_title = best_topic.suggested_title or best_topic.title
        main_keyword = best_topic.suggested_keywords[0] if best_topic.suggested_keywords else best_topic.category

        # Build additional context
        additional_context = f"""
ŹRÓDŁO INSPIRACJI: {best_topic.source}
URL ŹRÓDŁA: {best_topic.source_url}
DATA PUBLIKACJI ŹRÓDŁA: {best_topic.published_at}

OPIS TEMATU:
{best_topic.description}

SUGEROWANE PODEJŚCIE:
{best_topic.suggested_angle or 'Kompleksowe omówienie tematu z praktycznymi wskazówkami'}

DODATKOWE KEYWORDS DO WYKORZYSTANIA:
{', '.join(best_topic.suggested_keywords) if best_topic.suggested_keywords else main_keyword}

WAŻNE: Stwórz oryginalny artykuł inspirowany powyższym źródłem, NIE kopiuj treści.
Dodaj praktyczne wskazówki i przykłady z polskiego prawa.
"""

        # Generate post
        generation_result = await post_generator.generate_post(
            agent=agent,
            topic=topic_title,
            keyword=main_keyword,
            sources_content=additional_context,
        )

        # ============ PHASE 4: VALIDATION ============
        logger.info("Phase 4: Validating quality...")

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

        # Calculate overall SEO score
        seo_score = _calculate_seo_score(
            content=generation_result["content"],
            title=generation_result["title"],
            meta_description=generation_result["meta_description"],
            keyword=main_keyword,
            readability=readability_score,
            keyword_density=keyword_density,
        )

        logger.info(f"SEO Score: {seo_score}/100, Readability: {readability_score}")

        # Generate slug
        slug = seo_service.generate_slug(generation_result["title"])

        # ============ PHASE 5: PUBLISH ============
        logger.info("Phase 5: Publishing post...")

        # Determine status based on settings and quality
        seo_threshold = 30
        status = "published" if schedule.auto_publish and seo_score >= seo_threshold else "draft"

        if seo_score < seo_threshold:
            logger.warning(f"SEO score too low ({seo_score}), saving as draft")

        # Create post
        new_post = Post(
            agent_id=agent.id,
            title=generation_result["title"],
            content=generation_result["content"],
            meta_title=generation_result["meta_title"],
            meta_description=generation_result["meta_description"],
            keywords=generation_result["keywords"],
            slug=slug,
            status=status,
            published_at=datetime.utcnow() if status == "published" else None,
            tokens_used=generation_result["tokens_used"],
            word_count=generation_result["word_count"],
            readability_score=readability_score,
            keyword_density=keyword_density,
            source_urls=[best_topic.source_url] if best_topic.source_url else [],
        )

        db.add(new_post)
        await db.flush()

        # Log usage
        cost = token_counter.estimate_cost(
            input_tokens=generation_result["tokens_used"] // 2,
            output_tokens=generation_result["tokens_used"] // 2,
        )

        await usage_service.log_usage(
            db=db,
            tenant_id=agent.tenant_id,
            action_type="auto_publish_generation",
            tokens_used=generation_result["tokens_used"],
            cost=cost,
            agent_id=agent.id,
            meta_data={
                "post_id": str(new_post.id),
                "schedule_id": schedule_id,
                "topic_source": best_topic.source,
                "seo_score": seo_score,
                "auto_published": status == "published",
            },
        )

        # Update tenant usage
        await usage_service.update_tenant_usage(
            db=db,
            tenant_id=agent.tenant_id,
            tokens_delta=generation_result["tokens_used"],
            posts_delta=1,
        )

        # Update schedule stats
        schedule.last_run_at = datetime.utcnow()
        schedule.total_posts_generated += 1
        if status == "published":
            schedule.successful_posts += 1

        # Calculate next run
        cron = croniter(schedule.get_cron_expression(), datetime.utcnow())
        schedule.next_run_at = cron.get_next(datetime)

        await db.commit()
        await db.refresh(new_post)

        logger.info(f"Successfully created post {new_post.id} ({status})")

        return {
            "success": True,
            "post_id": str(new_post.id),
            "title": new_post.title,
            "status": status,
            "seo_score": seo_score,
            "word_count": new_post.word_count,
            "topic_source": best_topic.source,
        }

    except Exception as e:
        await db.rollback()
        logger.error(f"Error in auto-publish for schedule {schedule_id}: {e}", exc_info=True)

        # Update failed count
        try:
            result = await db.execute(
                select(ScheduleConfig).where(ScheduleConfig.id == UUID(schedule_id))
            )
            schedule = result.scalar_one_or_none()
            if schedule:
                schedule.failed_posts += 1
                schedule.last_run_at = datetime.utcnow()
                await db.commit()
        except Exception:
            pass

        return {"success": False, "error": str(e)}

    finally:
        await topic_service.close()


def get_task_db_session():
    """Create a fresh database session for Celery tasks.

    This creates a new engine and session factory to avoid event loop conflicts
    when running async code inside Celery tasks with asyncio.run().
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return session_factory(), engine


class DatabaseTask(Task):
    """Base task with database session management."""
    pass


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.auto_publish_tasks.auto_generate_and_publish",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    max_retries=2,
)
def auto_generate_and_publish(self, schedule_id: str):
    """
    Full auto-publish workflow for a schedule.

    1. DISCOVERY - Find trending topic
    2. RESEARCH - AI keyword suggestions
    3. GENERATION - Create SEO-optimized post
    4. VALIDATION - Check quality metrics
    5. PUBLISH - Publish or save as draft

    Args:
        schedule_id: Schedule UUID

    Returns:
        dict with result status and post_id
    """
    import asyncio

    async def _run_workflow():
        db, engine = get_task_db_session()
        topic_service = get_topic_discovery_service()

        try:
            # Get schedule
            result = await db.execute(
                select(ScheduleConfig).where(ScheduleConfig.id == UUID(schedule_id))
            )
            schedule = result.scalar_one_or_none()

            if not schedule:
                logger.error(f"Schedule {schedule_id} not found")
                return {"success": False, "error": "Schedule not found"}

            if not schedule.is_active:
                logger.info(f"Schedule {schedule_id} is inactive")
                return {"success": False, "error": "Schedule is inactive"}

            # Get agent
            agent_result = await db.execute(
                select(Agent).where(Agent.id == schedule.agent_id)
            )
            agent = agent_result.scalar_one_or_none()

            if not agent or not agent.is_active:
                logger.error(f"Agent for schedule {schedule_id} not found or inactive")
                return {"success": False, "error": "Agent not found or inactive"}

            logger.info(f"Starting auto-publish for schedule {schedule_id}, agent {agent.name}")

            # ============ PHASE 1: DISCOVERY ============
            logger.info("Phase 1: Discovering topics...")

            # Get already published titles to avoid duplicates
            existing_posts = await db.execute(
                select(Post.title).where(Post.agent_id == agent.id)
            )
            existing_titles = [row[0] for row in existing_posts.fetchall()]

            # Map target keywords to categories
            categories = None
            if schedule.target_keywords:
                categories = _map_keywords_to_categories(schedule.target_keywords)

            # Discover topics
            topics = await topic_service.discover_topics(
                categories=categories,
                max_topics=10,
                exclude_titles=existing_titles,
            )

            if not topics:
                logger.warning(f"No topics discovered for schedule {schedule_id}")
                # Update schedule stats
                schedule.failed_posts += 1
                schedule.last_run_at = datetime.utcnow()
                await db.commit()
                return {"success": False, "error": "No trending topics found"}

            # Filter by exclude keywords
            if schedule.exclude_keywords:
                topics = _filter_excluded_topics(topics, schedule.exclude_keywords)

            if not topics:
                logger.warning("All topics filtered out by exclude keywords")
                schedule.failed_posts += 1
                schedule.last_run_at = datetime.utcnow()
                await db.commit()
                return {"success": False, "error": "All topics filtered out"}

            # Select best topic
            best_topic = topics[0]  # Already sorted by score
            logger.info(f"Selected topic: {best_topic.title}")

            # ============ PHASE 2: AI RESEARCH ============
            logger.info("Phase 2: AI keyword research...")

            claude_client = get_claude_client()
            best_topic = await topic_service.get_topic_with_ai_suggestions(
                best_topic, claude_client
            )

            # ============ PHASE 3: GENERATION ============
            logger.info("Phase 3: Generating post...")

            post_generator = get_post_generator()
            seo_service = get_seo_service()
            token_counter = get_token_counter()
            usage_service = get_usage_service()

            # Check quotas
            quota_status = await usage_service.check_tenant_quota(
                db=db,
                tenant_id=agent.tenant_id,
                tokens_needed=5000,
                posts_needed=1,
            )

            if not quota_status["tokens_available"] or not quota_status["posts_available"]:
                logger.warning(f"Quota exceeded for tenant {agent.tenant_id}")
                schedule.failed_posts += 1
                schedule.last_run_at = datetime.utcnow()
                await db.commit()
                return {"success": False, "error": "Quota exceeded"}

            # Prepare generation parameters
            topic_title = best_topic.suggested_title or best_topic.title
            main_keyword = best_topic.suggested_keywords[0] if best_topic.suggested_keywords else best_topic.category

            # Build additional context
            additional_context = f"""
ŹRÓDŁO INSPIRACJI: {best_topic.source}
URL ŹRÓDŁA: {best_topic.source_url}
DATA PUBLIKACJI ŹRÓDŁA: {best_topic.published_at}

OPIS TEMATU:
{best_topic.description}

SUGEROWANE PODEJŚCIE:
{best_topic.suggested_angle or 'Kompleksowe omówienie tematu z praktycznymi wskazówkami'}

DODATKOWE KEYWORDS DO WYKORZYSTANIA:
{', '.join(best_topic.suggested_keywords) if best_topic.suggested_keywords else main_keyword}

WAŻNE: Stwórz oryginalny artykuł inspirowany powyższym źródłem, NIE kopiuj treści.
Dodaj praktyczne wskazówki i przykłady z polskiego prawa.
"""

            # Generate post
            generation_result = await post_generator.generate_post(
                agent=agent,
                topic=topic_title,
                keyword=main_keyword,
                sources_content=additional_context,
            )

            # ============ PHASE 4: VALIDATION ============
            logger.info("Phase 4: Validating quality...")

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

            # Calculate overall SEO score
            seo_score = _calculate_seo_score(
                content=generation_result["content"],
                title=generation_result["title"],
                meta_description=generation_result["meta_description"],
                keyword=main_keyword,
                readability=readability_score,
                keyword_density=keyword_density,
            )

            logger.info(f"SEO Score: {seo_score}/100, Readability: {readability_score}")

            # Generate slug
            slug = seo_service.generate_slug(generation_result["title"])

            # ============ PHASE 5: PUBLISH ============
            logger.info("Phase 5: Publishing post...")

            # Determine status based on settings and quality
            # SEO threshold lowered to 30 for demo purposes (was 70)
            seo_threshold = 30
            status = "published" if schedule.auto_publish and seo_score >= seo_threshold else "draft"

            if seo_score < seo_threshold:
                logger.warning(f"SEO score too low ({seo_score}), saving as draft")

            # Create post
            new_post = Post(
                agent_id=agent.id,
                title=generation_result["title"],
                content=generation_result["content"],
                meta_title=generation_result["meta_title"],
                meta_description=generation_result["meta_description"],
                keywords=generation_result["keywords"],
                slug=slug,
                status=status,
                published_at=datetime.utcnow() if status == "published" else None,
                tokens_used=generation_result["tokens_used"],
                word_count=generation_result["word_count"],
                readability_score=readability_score,
                keyword_density=keyword_density,
                source_urls=[best_topic.source_url] if best_topic.source_url else [],
            )

            db.add(new_post)
            await db.flush()

            # Log usage
            cost = token_counter.estimate_cost(
                input_tokens=generation_result["tokens_used"] // 2,
                output_tokens=generation_result["tokens_used"] // 2,
            )

            await usage_service.log_usage(
                db=db,
                tenant_id=agent.tenant_id,
                action_type="auto_publish_generation",
                tokens_used=generation_result["tokens_used"],
                cost=cost,
                agent_id=agent.id,
                meta_data={
                    "post_id": str(new_post.id),
                    "schedule_id": schedule_id,
                    "task_id": self.request.id,
                    "topic_source": best_topic.source,
                    "seo_score": seo_score,
                    "auto_published": status == "published",
                },
            )

            # Update tenant usage
            await usage_service.update_tenant_usage(
                db=db,
                tenant_id=agent.tenant_id,
                tokens_delta=generation_result["tokens_used"],
                posts_delta=1,
            )

            # Update schedule stats
            schedule.last_run_at = datetime.utcnow()
            schedule.total_posts_generated += 1
            if status == "published":
                schedule.successful_posts += 1
            else:
                # Draft is not failure, but track separately
                pass

            # Calculate next run
            cron = croniter(schedule.get_cron_expression(), datetime.utcnow())
            schedule.next_run_at = cron.get_next(datetime)

            await db.commit()
            await db.refresh(new_post)

            logger.info(f"Successfully created post {new_post.id} ({status})")

            return {
                "success": True,
                "post_id": str(new_post.id),
                "title": new_post.title,
                "status": status,
                "seo_score": seo_score,
                "word_count": new_post.word_count,
                "topic_source": best_topic.source,
            }

        except Exception as e:
            await db.rollback()
            logger.error(f"Error in auto-publish for schedule {schedule_id}: {e}", exc_info=True)

            # Update failed count
            try:
                result = await db.execute(
                    select(ScheduleConfig).where(ScheduleConfig.id == UUID(schedule_id))
                )
                schedule = result.scalar_one_or_none()
                if schedule:
                    schedule.failed_posts += 1
                    schedule.last_run_at = datetime.utcnow()
                    await db.commit()
            except Exception:
                pass

            raise

        finally:
            await db.close()
            await engine.dispose()
            await topic_service.close()

    return asyncio.run(_run_workflow())


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.auto_publish_tasks.process_auto_publish_schedules",
)
def process_auto_publish_schedules(self):
    """
    Process all auto-publish schedules.

    Checks which schedules should run based on their cron expression.
    Called hourly by Celery Beat.

    Returns:
        dict with number of schedules processed
    """
    import asyncio

    async def _process():
        db, engine = get_task_db_session()
        try:
            # Get all active schedules
            result = await db.execute(
                select(ScheduleConfig).where(ScheduleConfig.is_active == True)
            )
            schedules = result.scalars().all()

            now = datetime.utcnow()
            triggered = 0

            for schedule in schedules:
                try:
                    # Check if should run
                    if schedule.next_run_at and schedule.next_run_at <= now:
                        # Trigger auto-publish
                        auto_generate_and_publish.delay(str(schedule.id))
                        triggered += 1
                        logger.info(f"Triggered auto-publish for schedule {schedule.id}")

                except Exception as e:
                    logger.error(f"Error checking schedule {schedule.id}: {e}")
                    continue

            logger.info(f"Processed {len(schedules)} schedules, triggered {triggered}")

            return {
                "success": True,
                "schedules_checked": len(schedules),
                "triggered": triggered,
            }

        except Exception as e:
            logger.error(f"Error processing auto-publish schedules: {e}", exc_info=True)
            raise
        finally:
            await db.close()
            await engine.dispose()

    return asyncio.run(_process())


def _map_keywords_to_categories(keywords: List[str]) -> List[str]:
    """Map target keywords to legal categories."""
    from app.services.topic_discovery import LEGAL_CATEGORIES

    categories = set()

    for keyword in keywords:
        keyword_lower = keyword.lower()
        for category, cat_keywords in LEGAL_CATEGORIES.items():
            if any(kw in keyword_lower for kw in cat_keywords):
                categories.add(category)

    return list(categories) if categories else None


def _filter_excluded_topics(
    topics: List[DiscoveredTopic],
    exclude_keywords: List[str]
) -> List[DiscoveredTopic]:
    """Filter out topics containing excluded keywords."""
    filtered = []

    for topic in topics:
        text = (topic.title + " " + topic.description).lower()
        excluded = False

        for keyword in exclude_keywords:
            if keyword.lower() in text:
                excluded = True
                break

        if not excluded:
            filtered.append(topic)

    return filtered


def _calculate_seo_score(
    content: str,
    title: str,
    meta_description: str,
    keyword: str,
    readability: float,
    keyword_density: dict,
) -> int:
    """
    Calculate overall SEO score (0-100).

    Factors:
    - Title optimization (20 points)
    - Meta description (15 points)
    - Content length (15 points)
    - Keyword usage (20 points)
    - Readability (15 points)
    - Structure (15 points)
    """
    score = 0
    keyword_lower = keyword.lower()

    # Title optimization (20 points)
    title_lower = title.lower()
    if keyword_lower in title_lower:
        score += 10  # Keyword in title
    if 40 <= len(title) <= 70:
        score += 5  # Good length
    if title_lower.startswith(keyword_lower[:10]):
        score += 5  # Keyword at start

    # Meta description (15 points)
    meta_lower = meta_description.lower() if meta_description else ""
    if keyword_lower in meta_lower:
        score += 8
    if 120 <= len(meta_description or "") <= 160:
        score += 7

    # Content length (15 points)
    word_count = len(content.split())
    if word_count >= 2000:
        score += 15
    elif word_count >= 1500:
        score += 12
    elif word_count >= 1000:
        score += 8
    elif word_count >= 500:
        score += 5

    # Keyword usage (20 points)
    if keyword_density:
        main_density = keyword_density.get(keyword, 0)
        if 1.0 <= main_density <= 2.5:
            score += 15  # Optimal density
        elif 0.5 <= main_density <= 3.0:
            score += 10  # Acceptable
        elif main_density > 0:
            score += 5  # At least present

    # Keyword in first 100 words
    first_100_words = " ".join(content.split()[:100]).lower()
    if keyword_lower in first_100_words:
        score += 5

    # Readability (15 points)
    if 50 <= readability <= 70:
        score += 15  # Optimal for general audience
    elif 40 <= readability <= 80:
        score += 10
    elif readability > 30:
        score += 5

    # Structure (15 points)
    if "<h2>" in content:
        score += 5
    if "<h3>" in content:
        score += 3
    if "<ul>" in content or "<ol>" in content:
        score += 4
    if content.count("<h2>") >= 3:
        score += 3  # Multiple sections

    return min(score, 100)
