"""
Sources API endpoints - manage knowledge sources for agents.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.source import Source
from app.models.agent import Agent
from app.models.user import User
from app.schemas.source import (
    SourceCreate,
    SourceUpdate,
    SourceResponse,
    SourceTestRequest,
    SourceTestResponse
)
from app.api.deps import get_current_user, get_agent_with_access
from app.adapters import create_source_adapter

router = APIRouter(prefix="/agents/{agent_id}/sources", tags=["Sources"])

# Tenant-level endpoints (without agent_id requirement)
tenant_router = APIRouter(prefix="/sources", tags=["Sources"])


@router.get("", response_model=List[SourceResponse])
async def list_sources(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all sources for an agent."""
    agent = await get_agent_with_access(agent_id, db, current_user)

    result = await db.execute(
        select(Source)
        .where(Source.agent_id == agent.id)
        .order_by(Source.created_at.desc())
    )
    sources = result.scalars().all()
    return sources


@router.post("", response_model=SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_source(
    agent_id: UUID,
    source_data: SourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new source for agent."""
    agent = await get_agent_with_access(agent_id, db, current_user)

    new_source = Source(
        agent_id=agent.id,
        type=source_data.type,
        name=source_data.name,
        url=source_data.url,
        config=source_data.config or {}
    )

    db.add(new_source)
    await db.commit()
    await db.refresh(new_source)

    return new_source


@router.put("/{source_id}", response_model=SourceResponse)
async def update_source(
    agent_id: UUID,
    source_id: UUID,
    source_data: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update source."""
    agent = await get_agent_with_access(agent_id, db, current_user)

    result = await db.execute(
        select(Source).where(
            Source.id == source_id,
            Source.agent_id == agent.id
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    # Update fields
    update_data = source_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(source, field, value)

    await db.commit()
    await db.refresh(source)

    return source


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(
    agent_id: UUID,
    source_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete source."""
    agent = await get_agent_with_access(agent_id, db, current_user)

    result = await db.execute(
        select(Source).where(
            Source.id == source_id,
            Source.agent_id == agent.id
        )
    )
    source = result.scalar_one_or_none()

    if not source:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source not found",
        )

    await db.delete(source)
    await db.commit()


@router.post("/test", response_model=SourceTestResponse)
async def test_source(
    test_data: SourceTestRequest,
    _: User = Depends(get_current_user)
):
    """
    Test source connection/configuration without saving.

    Tests if the source configuration is valid and can fetch content.
    """
    try:
        # Create adapter instance
        adapter = create_source_adapter(test_data.type, test_data.config)

        # Test connection
        result = await adapter.test_connection()

        return SourceTestResponse(
            success=result["success"],
            message=result["message"],
            data=result
        )

    except ValueError as e:
        # Unknown adapter type
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Adapter error
        return SourceTestResponse(
            success=False,
            message="Test failed",
            data={"error": str(e)}
        )


# Tenant-level endpoint (list all sources for current user's tenant)
@tenant_router.get("", response_model=List[SourceResponse])
async def list_all_tenant_sources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all sources across all agents for the current user's tenant."""
    # Get all agents for this tenant
    agents_result = await db.execute(
        select(Agent).where(Agent.tenant_id == current_user.tenant_id)
    )
    agent_ids = [agent.id for agent in agents_result.scalars().all()]

    # Get all sources for these agents
    if not agent_ids:
        return []

    result = await db.execute(
        select(Source)
        .where(Source.agent_id.in_(agent_ids))
        .order_by(Source.created_at.desc())
    )
    sources = result.scalars().all()
    return sources
