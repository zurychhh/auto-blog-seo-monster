"""
Agents API endpoints - CRUD operations for AI agents.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.agent import Agent
from app.models.user import User
from app.models.tenant import Tenant
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse, AgentRunRequest
from app.api.deps import get_current_user, get_current_tenant

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """List all agents for current tenant."""
    # Superadmin can see all agents, regular users see only their tenant's
    if current_user.is_superadmin():
        result = await db.execute(
            select(Agent)
            .offset(skip)
            .limit(limit)
            .order_by(Agent.created_at.desc())
        )
    else:
        result = await db.execute(
            select(Agent)
            .where(Agent.tenant_id == tenant.id)
            .offset(skip)
            .limit(limit)
            .order_by(Agent.created_at.desc())
        )

    agents = result.scalars().all()
    return agents


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    tenant: Tenant = Depends(get_current_tenant)
):
    """Create new agent."""
    # Regular users can only create agents in their tenant
    # Superadmin would need to specify tenant_id (not implemented here for simplicity)

    new_agent = Agent(
        tenant_id=tenant.id,
        name=agent_data.name,
        expertise=agent_data.expertise,
        persona=agent_data.persona,
        tone=agent_data.tone,
        post_length=agent_data.post_length,
        schedule_cron=agent_data.schedule_cron,
        workflow=agent_data.workflow,
        settings=agent_data.settings or {}
    )

    db.add(new_agent)
    await db.commit()
    await db.refresh(new_agent)

    return new_agent


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get agent by ID."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check access
    if not current_user.is_superadmin() and agent.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: UUID,
    agent_data: AgentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update agent."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check access
    if not current_user.is_superadmin() and agent.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    # Update fields
    update_data = agent_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agent, field, value)

    await db.commit()
    await db.refresh(agent)

    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete agent."""
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check access
    if not current_user.is_superadmin() and agent.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await db.delete(agent)
    await db.commit()


@router.post("/{agent_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_agent(
    agent_id: UUID,
    run_data: AgentRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger agent to generate content.

    This will be implemented in Phase 2 with AI Engine.
    For now, just a placeholder that returns accepted status.
    """
    result = await db.execute(
        select(Agent).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    # Check access
    if not current_user.is_superadmin() and agent.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is inactive",
        )

    # TODO: Phase 2 - Trigger Celery task to generate content
    # from app.tasks.content_tasks import generate_agent_content
    # generate_agent_content.delay(str(agent_id), run_data.topic)

    return {
        "message": "Agent run queued",
        "agent_id": str(agent_id),
        "status": "queued"
    }
