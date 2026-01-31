"""
Tenants API endpoints - superadmin only.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantUsageResponse
)
from app.api.deps import get_current_superadmin, get_current_user

router = APIRouter(prefix="/tenants", tags=["Tenants"])


@router.get("/me", response_model=TenantResponse)
async def get_current_tenant(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's tenant."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin)
):
    """List all tenants (superadmin only)."""
    result = await db.execute(
        select(Tenant)
        .offset(skip)
        .limit(limit)
        .order_by(Tenant.created_at.desc())
    )
    tenants = result.scalars().all()
    return tenants


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    tenant_data: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin)
):
    """Create new tenant (superadmin only)."""
    # Check if slug already exists
    result = await db.execute(
        select(Tenant).where(Tenant.slug == tenant_data.slug)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant with this slug already exists",
        )

    # Create tenant
    new_tenant = Tenant(
        name=tenant_data.name,
        slug=tenant_data.slug,
        tokens_limit=tenant_data.tokens_limit,
        posts_limit=tenant_data.posts_limit,
        settings=tenant_data.settings or {}
    )

    db.add(new_tenant)
    await db.commit()
    await db.refresh(new_tenant)

    return new_tenant


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin)
):
    """Get tenant by ID (superadmin only)."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin)
):
    """Update tenant (superadmin only)."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Update fields
    update_data = tenant_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin)
):
    """Soft delete tenant (superadmin only)."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    # Soft delete by deactivating
    tenant.is_active = False
    await db.commit()


@router.get("/{tenant_id}/usage", response_model=TenantUsageResponse)
async def get_tenant_usage(
    tenant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_superadmin)
):
    """Get tenant usage statistics (superadmin only)."""
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return TenantUsageResponse(
        tenant_id=tenant.id,
        tokens_used=tenant.tokens_used,
        tokens_limit=tenant.tokens_limit,
        tokens_percentage=(tenant.tokens_used / tenant.tokens_limit * 100) if tenant.tokens_limit > 0 else 0,
        posts_used=tenant.posts_used,
        posts_limit=tenant.posts_limit,
        posts_percentage=(tenant.posts_used / tenant.posts_limit * 100) if tenant.posts_limit > 0 else 0,
    )
