"""
Public API endpoints - accessible without authentication.
For displaying published blog posts on landing pages.
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

from app.database import get_db
from app.models.post import Post
from app.models.tenant import Tenant
from app.models.user import User
from app.models.agent import Agent
from app.schemas.post import PostResponse, PostListResponse
from app.config import settings
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/posts", response_model=PostListResponse)
async def list_public_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    agent_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    List published posts - PUBLIC endpoint (no authentication required).
    Only returns posts with status='published'.
    Optionally filter by agent_id.
    """
    # Build query for published posts only
    query = select(Post).where(Post.status == "published")

    # Filter by agent_id if provided
    if agent_id:
        query = query.where(Post.agent_id == agent_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results - order by published_at, fallback to created_at for NULLs
    order_column = func.coalesce(Post.published_at, Post.created_at)
    query = query.order_by(order_column.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    posts = result.scalars().all()

    return PostListResponse(
        items=posts,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )


@router.get("/posts/slug/{slug}", response_model=PostResponse)
async def get_public_post_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Get published post by slug - PUBLIC endpoint (no authentication required).
    Only returns posts with status='published'.
    """
    result = await db.execute(
        select(Post).where(
            Post.slug == slug,
            Post.status == "published"
        )
    )
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Post not found",
        )

    return post


@router.get("/posts/featured", response_model=List[PostResponse])
async def get_featured_posts(
    limit: int = Query(3, ge=1, le=10),
    agent_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Get featured published posts - PUBLIC endpoint.
    Returns the most recent published posts (default: 3).
    Perfect for landing page "Knowledge Base" section.
    Optionally filter by agent_id.
    """
    order_column = func.coalesce(Post.published_at, Post.created_at)
    query = select(Post).where(Post.status == "published")

    if agent_id:
        query = query.where(Post.agent_id == agent_id)

    query = query.order_by(order_column.desc()).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().all()

    return posts


@router.post("/setup/fix-admin")
async def fix_admin_user(
    x_setup_key: str = Header(..., alias="X-Setup-Key"),
    db: AsyncSession = Depends(get_db)
):
    """
    One-time setup endpoint to fix admin user tenant association.
    Requires X-Setup-Key header matching SECRET_KEY.
    """
    # Verify secret key (using JWT_SECRET)
    if x_setup_key != settings.JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid setup key"
        )

    # Get Legitio tenant
    result = await db.execute(
        select(Tenant).where(Tenant.slug == "legitio")
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        return {"status": "error", "message": "Legitio tenant not found"}

    # Get admin user
    result = await db.execute(
        select(User).where(User.email == "admin@legitio.pl")
    )
    admin = result.scalar_one_or_none()

    if not admin:
        return {"status": "error", "message": "Admin user not found"}

    # Check current state
    old_tenant_id = admin.tenant_id
    old_role = admin.role

    # Update admin user
    admin.tenant_id = tenant.id
    admin.role = "admin"
    await db.commit()

    return {
        "status": "success",
        "message": "Admin user fixed",
        "admin_email": admin.email,
        "tenant_name": tenant.name,
        "tenant_id": str(tenant.id),
        "old_tenant_id": str(old_tenant_id) if old_tenant_id else None,
        "old_role": old_role
    }


@router.post("/setup/seed-oleksiak")
async def seed_oleksiak_tenant(
    x_setup_key: str = Header(..., alias="X-Setup-Key"),
    db: AsyncSession = Depends(get_db)
):
    """
    One-time setup: create Oleksiak Consulting tenant, agent, and superadmin user.
    Requires X-Setup-Key header matching JWT_SECRET.
    """
    if x_setup_key != settings.JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid setup key"
        )

    # Check if tenant already exists
    result = await db.execute(
        select(Tenant).where(Tenant.slug == "oleksiak-consulting")
    )
    existing_tenant = result.scalar_one_or_none()

    if existing_tenant:
        # Tenant exists — just return info
        result = await db.execute(
            select(Agent).where(Agent.tenant_id == existing_tenant.id)
        )
        agent = result.scalar_one_or_none()
        result = await db.execute(
            select(User).where(User.email == "rafal@oleksiakconsulting.com")
        )
        user = result.scalar_one_or_none()
        return {
            "status": "already_exists",
            "tenant_id": str(existing_tenant.id),
            "agent_id": str(agent.id) if agent else None,
            "user_email": user.email if user else None,
            "user_role": user.role if user else None,
        }

    # 1. Create tenant
    tenant = Tenant(
        name="Oleksiak Consulting",
        slug="oleksiak-consulting",
        is_active=True,
        tokens_limit=500000,
        posts_limit=200,
    )
    db.add(tenant)
    await db.flush()

    # 2. Create agent
    agent = Agent(
        tenant_id=tenant.id,
        name="Oleksiak Blog Agent",
        expertise="ecommerce-marketing",
        persona=(
            "You are a senior ecommerce and marketing consultant writing for "
            "Oleksiak Consulting blog. You write in English about ecommerce strategy, "
            "conversion optimization, CRM, marketing automation, and digital growth. "
            "Your tone is professional yet accessible, backed by data and real examples."
        ),
        tone="professional",
        post_length="long",
        workflow="draft",
        is_active=True,
        settings={
            "target_audience": "ecommerce managers, marketing directors, business owners",
            "topics": ["ecommerce", "CRM", "conversion optimization", "marketing automation",
                       "digital strategy", "growth hacking", "analytics"],
        },
    )
    db.add(agent)
    await db.flush()

    # 3. Create superadmin user
    password_hash = AuthService.hash_password("OleksiakAdmin2025!")
    user = User(
        tenant_id=None,  # superadmin has no tenant
        email="rafal@oleksiakconsulting.com",
        password_hash=password_hash,
        role="superadmin",
        is_active=True,
    )
    db.add(user)

    # 4. Also promote existing admin@legitio.pl to superadmin
    result = await db.execute(
        select(User).where(User.email == "admin@legitio.pl")
    )
    legitio_admin = result.scalar_one_or_none()
    if legitio_admin:
        legitio_admin.role = "superadmin"
        legitio_admin.tenant_id = None

    await db.commit()

    return {
        "status": "success",
        "message": "Oleksiak Consulting tenant seeded",
        "tenant_id": str(tenant.id),
        "tenant_slug": tenant.slug,
        "agent_id": str(agent.id),
        "agent_name": agent.name,
        "user_email": user.email,
        "user_role": user.role,
        "legitio_admin_promoted": legitio_admin is not None,
    }
