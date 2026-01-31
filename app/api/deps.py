"""
API dependencies for authentication, database, and authorization.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.services.auth_service import AuthService

# Security scheme for JWT Bearer tokens
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Get current authenticated user from JWT token.

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token
    token_data = AuthService.decode_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get user from database
    user = await AuthService.get_user_by_id(db, token_data.sub)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Get current active user.
    Alias for get_current_user (kept for compatibility).
    """
    return current_user


def require_role(required_role: str):
    """
    Dependency factory to require specific role.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])

    Args:
        required_role: Minimum required role (superadmin > admin > editor)
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if not current_user.has_role(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role or higher",
            )
        return current_user

    return role_checker


async def get_current_superadmin(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require superadmin role."""
    if not current_user.is_superadmin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superadmin access required",
        )
    return current_user


async def get_current_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    """
    Get current user's tenant.

    Raises:
        HTTPException: 403 if user has no tenant (e.g., superadmin)
    """
    if not current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tenant associated with this user",
        )

    from sqlalchemy import select
    result = await db.execute(
        select(Tenant).where(Tenant.id == current_user.tenant_id)
    )
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant is inactive",
        )

    return tenant


async def verify_tenant_access(
    tenant_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Verify user has access to specific tenant.

    Args:
        tenant_id: Tenant UUID to check access for
        current_user: Current authenticated user

    Raises:
        HTTPException: 403 if user doesn't have access
    """
    # Superadmin has access to all tenants
    if current_user.is_superadmin():
        return

    # Regular users can only access their own tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this tenant",
        )


async def get_agent_with_access(
    agent_id: UUID,
    db: AsyncSession,
    current_user: User
):
    """
    Helper to get agent and verify user has access.

    Args:
        agent_id: Agent UUID
        db: Database session
        current_user: Current authenticated user

    Returns:
        Agent object if found and accessible

    Raises:
        HTTPException: 404 if agent not found, 403 if no access
    """
    from app.models.agent import Agent
    from sqlalchemy import select

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
