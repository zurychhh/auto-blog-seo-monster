"""
Public API endpoints - accessible without authentication.
For displaying published blog posts on landing pages.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
import logging

from app.database import get_db
from app.models.post import Post
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.post import PostResponse, PostListResponse
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/posts", response_model=PostListResponse)
async def list_public_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    List published posts - PUBLIC endpoint (no authentication required).
    Only returns posts with status='published'.
    """
    # Build query for published posts only
    query = select(Post).where(Post.status == "published")

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
    db: AsyncSession = Depends(get_db)
):
    """
    Get featured published posts - PUBLIC endpoint.
    Returns the most recent published posts (default: 3).
    Perfect for landing page "Knowledge Base" section.
    """
    order_column = func.coalesce(Post.published_at, Post.created_at)
    query = (
        select(Post)
        .where(Post.status == "published")
        .order_by(order_column.desc())
        .limit(limit)
    )

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
