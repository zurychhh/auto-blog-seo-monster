"""
Schedule API endpoints - manage automatic post scheduling.
"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
import asyncio
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Header, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from croniter import croniter

from app.database import get_db
from app.models.schedule import ScheduleConfig, ScheduleInterval
from app.models.agent import Agent
from app.models.user import User
from app.api.deps import get_current_user
from app.config import settings
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    ScheduleRunResponse,
    ScheduleStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedules", tags=["Schedules"])


def schedule_to_response(schedule: ScheduleConfig) -> ScheduleResponse:
    """Convert ScheduleConfig model to response schema."""
    return ScheduleResponse(
        id=schedule.id,
        agent_id=schedule.agent_id,
        interval=schedule.interval,
        interval_display=schedule.get_interval_display(),
        publish_hour=schedule.publish_hour,
        timezone=schedule.timezone,
        cron_expression=schedule.get_cron_expression(),
        is_active=schedule.is_active,
        auto_publish=schedule.auto_publish,
        target_keywords=schedule.target_keywords,
        exclude_keywords=schedule.exclude_keywords,
        post_length=schedule.post_length,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        total_posts_generated=schedule.total_posts_generated,
        successful_posts=schedule.successful_posts,
        failed_posts=schedule.failed_posts,
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
    )


def calculate_next_run(cron_expr: str, from_time: datetime = None) -> datetime:
    """Calculate next run time based on cron expression."""
    if from_time is None:
        from_time = datetime.utcnow()
    cron = croniter(cron_expr, from_time)
    return cron.get_next(datetime)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new automatic post schedule."""
    # Verify agent exists and belongs to user's tenant
    result = await db.execute(
        select(Agent).where(
            Agent.id == schedule_data.agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check if schedule already exists for this agent
    existing = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.agent_id == schedule_data.agent_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule already exists for this agent. Update it instead.",
        )

    # Create schedule
    schedule = ScheduleConfig(
        agent_id=schedule_data.agent_id,
        interval=schedule_data.interval.value,
        publish_hour=schedule_data.publish_hour,
        timezone=schedule_data.timezone,
        auto_publish=schedule_data.auto_publish,
        target_keywords=schedule_data.target_keywords,
        exclude_keywords=schedule_data.exclude_keywords,
        post_length=schedule_data.post_length.value,
        is_active=schedule_data.is_active,
    )

    # Calculate next run time
    schedule.next_run_at = calculate_next_run(schedule.get_cron_expression())

    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return schedule_to_response(schedule)


@router.get("", response_model=ScheduleListResponse)
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all schedules for current tenant."""
    # Get agents for this tenant
    agents_result = await db.execute(
        select(Agent.id).where(Agent.tenant_id == current_user.tenant_id)
    )
    agent_ids = [row[0] for row in agents_result.fetchall()]

    if not agent_ids:
        return ScheduleListResponse(items=[], total=0)

    # Get schedules for these agents
    result = await db.execute(
        select(ScheduleConfig)
        .where(ScheduleConfig.agent_id.in_(agent_ids))
        .order_by(ScheduleConfig.created_at.desc())
    )
    schedules = result.scalars().all()

    return ScheduleListResponse(
        items=[schedule_to_response(s) for s in schedules],
        total=len(schedules),
    )


@router.get("/stats", response_model=ScheduleStats)
async def get_schedule_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get schedule statistics for current tenant."""
    # Get agents for this tenant
    agents_result = await db.execute(
        select(Agent.id, Agent.name).where(Agent.tenant_id == current_user.tenant_id)
    )
    agents = {row[0]: row[1] for row in agents_result.fetchall()}
    agent_ids = list(agents.keys())

    if not agent_ids:
        return ScheduleStats(
            total_schedules=0,
            active_schedules=0,
            total_posts_generated=0,
            successful_posts=0,
            failed_posts=0,
            success_rate=0.0,
            posts_last_7_days=0,
            posts_last_30_days=0,
            upcoming_posts=[],
        )

    # Get all schedules
    result = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.agent_id.in_(agent_ids))
    )
    schedules = result.scalars().all()

    total = len(schedules)
    active = sum(1 for s in schedules if s.is_active)
    total_generated = sum(s.total_posts_generated for s in schedules)
    successful = sum(s.successful_posts for s in schedules)
    failed = sum(s.failed_posts for s in schedules)

    success_rate = (successful / total_generated * 100) if total_generated > 0 else 0.0

    # Calculate upcoming posts
    now = datetime.utcnow()
    upcoming = []
    for s in schedules:
        if s.is_active and s.next_run_at:
            upcoming.append({
                "schedule_id": str(s.id),
                "next_run_at": s.next_run_at.isoformat(),
                "agent_name": agents.get(s.agent_id, "Unknown"),
                "interval": s.get_interval_display(),
            })

    upcoming.sort(key=lambda x: x["next_run_at"])

    return ScheduleStats(
        total_schedules=total,
        active_schedules=active,
        total_posts_generated=total_generated,
        successful_posts=successful,
        failed_posts=failed,
        success_rate=round(success_rate, 2),
        posts_last_7_days=0,  # TODO: Calculate from posts table
        posts_last_30_days=0,  # TODO: Calculate from posts table
        upcoming_posts=upcoming[:5],
    )


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get schedule by ID."""
    result = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    # Verify ownership
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == schedule.agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    if not agent_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return schedule_to_response(schedule)


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    update_data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an existing schedule."""
    result = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    # Verify ownership
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == schedule.agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    if not agent_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)

    if "interval" in update_dict:
        update_dict["interval"] = update_dict["interval"].value
    if "post_length" in update_dict:
        update_dict["post_length"] = update_dict["post_length"].value

    for key, value in update_dict.items():
        setattr(schedule, key, value)

    # Recalculate next run if interval or hour changed
    if "interval" in update_dict or "publish_hour" in update_dict:
        schedule.next_run_at = calculate_next_run(schedule.get_cron_expression())

    await db.commit()
    await db.refresh(schedule)

    return schedule_to_response(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a schedule."""
    result = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    # Verify ownership
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == schedule.agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    if not agent_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await db.delete(schedule)
    await db.commit()


@router.post("/{schedule_id}/run", response_model=ScheduleRunResponse)
async def run_schedule_now(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger a schedule to run now."""
    from app.tasks.auto_publish_tasks import auto_generate_and_publish

    result = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    # Verify ownership
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == schedule.agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    if not agent_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Trigger async task
    try:
        task = auto_generate_and_publish.delay(str(schedule_id))

        return ScheduleRunResponse(
            success=True,
            message="Task queued successfully",
            task_id=task.id,
        )
    except Exception as e:
        return ScheduleRunResponse(
            success=False,
            message=f"Failed to queue task: {str(e)}",
        )


@router.post("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle schedule active/inactive status."""
    result = await db.execute(
        select(ScheduleConfig).where(ScheduleConfig.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found",
        )

    # Verify ownership
    agent_result = await db.execute(
        select(Agent).where(
            Agent.id == schedule.agent_id,
            Agent.tenant_id == current_user.tenant_id,
        )
    )
    if not agent_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    schedule.is_active = not schedule.is_active

    # Update next_run if activating
    if schedule.is_active:
        schedule.next_run_at = calculate_next_run(schedule.get_cron_expression())
    else:
        schedule.next_run_at = None

    await db.commit()
    await db.refresh(schedule)

    return schedule_to_response(schedule)


# ============================================================================
# CRON TRIGGER ENDPOINT (for external cron services like cron-job.org)
# ============================================================================

async def run_auto_publish_for_schedule(schedule_id: str):
    """
    Run auto-publish workflow for a single schedule.
    This runs the same logic as the Celery task but synchronously.
    """
    from app.tasks.auto_publish_tasks import auto_generate_and_publish

    try:
        # Run the task synchronously (it uses asyncio.run internally)
        result = auto_generate_and_publish(schedule_id)
        logger.info(f"Auto-publish completed for schedule {schedule_id}: {result}")
        return result
    except Exception as e:
        logger.error(f"Auto-publish failed for schedule {schedule_id}: {e}")
        return {"success": False, "error": str(e)}


@router.post("/trigger-due", status_code=status.HTTP_202_ACCEPTED)
async def trigger_due_schedules(
    background_tasks: BackgroundTasks,
    x_cron_secret: Optional[str] = Header(None, alias="X-Cron-Secret"),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger all schedules that are due for execution.

    This endpoint is designed to be called by external cron services
    (e.g., cron-job.org, GitHub Actions) every hour.

    Authentication: X-Cron-Secret header must match CRON_SECRET env variable.
    If CRON_SECRET is not set, falls back to JWT_SECRET.

    Returns immediately with 202 Accepted, processing happens in background.
    """
    # Verify cron secret
    expected_secret = settings.CRON_SECRET or settings.JWT_SECRET
    if x_cron_secret != expected_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid cron secret"
        )

    now = datetime.utcnow()

    # Get all active schedules that are due
    result = await db.execute(
        select(ScheduleConfig).where(
            ScheduleConfig.is_active == True,
            ScheduleConfig.next_run_at <= now
        )
    )
    due_schedules = result.scalars().all()

    triggered_ids = []

    for schedule in due_schedules:
        try:
            # Update next_run_at immediately to prevent double-triggering
            schedule.next_run_at = calculate_next_run(schedule.get_cron_expression())
            await db.commit()

            # Add to background tasks
            background_tasks.add_task(
                run_auto_publish_for_schedule,
                str(schedule.id)
            )
            triggered_ids.append(str(schedule.id))
            logger.info(f"Triggered auto-publish for schedule {schedule.id}")

        except Exception as e:
            logger.error(f"Error triggering schedule {schedule.id}: {e}")
            continue

    return {
        "status": "accepted",
        "message": f"Triggered {len(triggered_ids)} schedule(s)",
        "triggered_schedules": triggered_ids,
        "checked_at": now.isoformat(),
    }
