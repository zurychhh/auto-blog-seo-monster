"""
Tasks API endpoints - manage and monitor Celery tasks.
"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from celery.result import AsyncResult

from app.models.user import User
from app.api.deps import get_current_user
from app.celery_app import celery_app

# Import tasks
from app.tasks import (
    generate_post_for_agent,
    publish_post,
    monitor_rss_feed,
    health_check,
    retry_failed_publications,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# Schemas
class TaskTrigger(BaseModel):
    """Request to trigger a task."""
    agent_id: Optional[UUID] = None
    post_id: Optional[UUID] = None
    source_id: Optional[UUID] = None
    publisher_id: Optional[UUID] = None
    topic: Optional[str] = None
    keyword: Optional[str] = None
    auto_generate: Optional[bool] = False


class TaskStatusResponse(BaseModel):
    """Task status response."""
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


class TaskListResponse(BaseModel):
    """List of active/scheduled tasks."""
    active: list[dict]
    scheduled: list[dict]
    reserved: list[dict]


# Endpoints

@router.post("/generate-post", status_code=status.HTTP_202_ACCEPTED)
async def trigger_post_generation(
    data: TaskTrigger,
    current_user: User = Depends(get_current_user)
):
    """
    Trigger asynchronous post generation.

    Returns task_id to check status later.
    """
    if not data.agent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="agent_id is required"
        )

    # Trigger task
    task = generate_post_for_agent.delay(
        str(data.agent_id),
        topic=data.topic,
        keyword=data.keyword
    )

    return {
        "task_id": task.id,
        "status": "pending",
        "message": "Post generation started",
    }


@router.post("/publish-post", status_code=status.HTTP_202_ACCEPTED)
async def trigger_post_publishing(
    data: TaskTrigger,
    current_user: User = Depends(get_current_user)
):
    """
    Trigger asynchronous post publishing.

    Returns task_id to check status later.
    """
    if not data.post_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="post_id is required"
        )

    # Trigger task
    task = publish_post.delay(
        str(data.post_id),
        publisher_id=str(data.publisher_id) if data.publisher_id else None
    )

    return {
        "task_id": task.id,
        "status": "pending",
        "message": "Post publishing started",
    }


@router.post("/monitor-rss", status_code=status.HTTP_202_ACCEPTED)
async def trigger_rss_monitoring(
    data: TaskTrigger,
    current_user: User = Depends(get_current_user)
):
    """
    Trigger RSS feed monitoring.

    Returns task_id to check status later.
    """
    if not data.source_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="source_id is required"
        )

    # Trigger task
    task = monitor_rss_feed.delay(
        str(data.source_id),
        auto_generate=data.auto_generate or False
    )

    return {
        "task_id": task.id,
        "status": "pending",
        "message": "RSS monitoring started",
    }


@router.post("/retry-failed", status_code=status.HTTP_202_ACCEPTED)
async def trigger_retry_failed(
    current_user: User = Depends(get_current_user)
):
    """
    Retry all failed post publications.

    Returns task_id to check status later.
    """
    # Only superadmin can trigger this
    if not current_user.is_superadmin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superadmin can trigger retry"
        )

    # Trigger task
    task = retry_failed_publications.delay()

    return {
        "task_id": task.id,
        "status": "pending",
        "message": "Retry process started",
    }


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get status of a specific task.

    Task statuses:
    - PENDING: Task is waiting to be executed
    - STARTED: Task has started
    - SUCCESS: Task completed successfully
    - FAILURE: Task failed
    - RETRY: Task is being retried
    - REVOKED: Task was cancelled
    """
    task_result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": task_result.state,
    }

    if task_result.ready():
        if task_result.successful():
            response["result"] = task_result.result
        else:
            response["error"] = str(task_result.info)

    return response


@router.delete("/cancel/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Cancel/revoke a pending or running task.

    Note: Already completed tasks cannot be cancelled.
    """
    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.state in ["PENDING", "STARTED", "RETRY"]:
        task_result.revoke(terminate=True)
        return {
            "message": "Task cancelled",
            "task_id": task_id,
        }
    else:
        return {
            "message": f"Task cannot be cancelled (status: {task_result.state})",
            "task_id": task_id,
            "status": task_result.state,
        }


@router.get("/active", response_model=TaskListResponse)
async def list_active_tasks(
    current_user: User = Depends(get_current_user)
):
    """
    List all active, scheduled, and reserved tasks.

    Requires Celery Inspect API.
    """
    inspect = celery_app.control.inspect()

    active_tasks = inspect.active() or {}
    scheduled_tasks = inspect.scheduled() or {}
    reserved_tasks = inspect.reserved() or {}

    return {
        "active": _flatten_task_dict(active_tasks),
        "scheduled": _flatten_task_dict(scheduled_tasks),
        "reserved": _flatten_task_dict(reserved_tasks),
    }


@router.get("/health")
async def check_celery_health():
    """
    Check if Celery workers are running.

    Triggers a health_check task and waits for result.
    """
    try:
        # Trigger health check task
        task = health_check.delay()

        # Wait for result (with timeout)
        result = task.get(timeout=5)

        return {
            "celery_status": "healthy",
            "workers_online": True,
            "health_check_result": result,
        }

    except Exception as e:
        return {
            "celery_status": "unhealthy",
            "workers_online": False,
            "error": str(e),
        }


def _flatten_task_dict(task_dict: dict) -> list:
    """Flatten nested task dictionary to list."""
    tasks = []
    for worker, task_list in task_dict.items():
        for task in task_list:
            task["worker"] = worker
            tasks.append(task)
    return tasks
