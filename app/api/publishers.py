"""
Publishers API endpoints - manage publication destinations for agents.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.publisher import Publisher
from app.models.agent import Agent
from app.models.user import User
from app.schemas.publisher import (
    PublisherCreate,
    PublisherUpdate,
    PublisherResponse,
    PublisherTestRequest,
    PublisherTestResponse
)
from app.api.deps import get_current_user, get_agent_with_access
from app.adapters import create_publisher_adapter

router = APIRouter(prefix="/agents/{agent_id}/publishers", tags=["Publishers"])

# Tenant-level endpoints (without agent_id requirement)
tenant_router = APIRouter(prefix="/publishers", tags=["Publishers"])


@router.get("", response_model=List[PublisherResponse])
async def list_publishers(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all publishers for an agent."""
    agent = await get_agent_with_access(agent_id, db, current_user)

    result = await db.execute(
        select(Publisher)
        .where(Publisher.agent_id == agent.id)
        .order_by(Publisher.created_at.desc())
    )
    publishers = result.scalars().all()
    return publishers


@router.post("", response_model=PublisherResponse, status_code=status.HTTP_201_CREATED)
async def create_publisher(
    agent_id: UUID,
    publisher_data: PublisherCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new publisher for agent."""
    agent = await get_agent_with_access(agent_id, db, current_user)

    new_publisher = Publisher(
        agent_id=agent.id,
        type=publisher_data.type,
        name=publisher_data.name,
        config=publisher_data.config
    )

    db.add(new_publisher)
    await db.commit()
    await db.refresh(new_publisher)

    return new_publisher


@router.put("/{publisher_id}", response_model=PublisherResponse)
async def update_publisher(
    agent_id: UUID,
    publisher_id: UUID,
    publisher_data: PublisherUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update publisher."""
    agent = await get_agent_with_access(agent_id, db, current_user)

    result = await db.execute(
        select(Publisher).where(
            Publisher.id == publisher_id,
            Publisher.agent_id == agent.id
        )
    )
    publisher = result.scalar_one_or_none()

    if not publisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    # Update fields
    update_data = publisher_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(publisher, field, value)

    await db.commit()
    await db.refresh(publisher)

    return publisher


@router.delete("/{publisher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_publisher(
    agent_id: UUID,
    publisher_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete publisher."""
    agent = await get_agent_with_access(agent_id, db, current_user)

    result = await db.execute(
        select(Publisher).where(
            Publisher.id == publisher_id,
            Publisher.agent_id == agent.id
        )
    )
    publisher = result.scalar_one_or_none()

    if not publisher:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Publisher not found",
        )

    await db.delete(publisher)
    await db.commit()


@router.post("/test", response_model=PublisherTestResponse)
async def test_publisher(
    test_data: PublisherTestRequest,
    _: User = Depends(get_current_user)
):
    """
    Test publisher connection/configuration without saving.

    Tests if the publisher configuration is valid and can connect to the platform.
    """
    try:
        # Create adapter instance
        adapter = create_publisher_adapter(test_data.type, test_data.config)

        # Test connection
        result = await adapter.test_connection()

        return PublisherTestResponse(
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
        return PublisherTestResponse(
            success=False,
            message="Test failed",
            data={"error": str(e)}
        )


# Tenant-level endpoint (list all publishers for current user's tenant)
@tenant_router.get("", response_model=List[PublisherResponse])
async def list_all_tenant_publishers(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all publishers across all agents for the current user's tenant."""
    # Get all agents for this tenant
    agents_result = await db.execute(
        select(Agent).where(Agent.tenant_id == current_user.tenant_id)
    )
    agent_ids = [agent.id for agent in agents_result.scalars().all()]

    # Get all publishers for these agents
    if not agent_ids:
        return []

    result = await db.execute(
        select(Publisher)
        .where(Publisher.agent_id.in_(agent_ids))
        .order_by(Publisher.created_at.desc())
    )
    publishers = result.scalars().all()
    return publishers
