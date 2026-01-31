"""
Usage tracking service - logs API usage and updates tenant quotas.
"""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.usage import UsageLog
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class UsageService:
    """Service for tracking API usage and managing quotas."""

    @staticmethod
    async def log_usage(
        db: AsyncSession,
        tenant_id: UUID,
        action_type: str,
        tokens_used: int,
        cost: float = 0.0,
        agent_id: Optional[UUID] = None,
        meta_data: Optional[dict] = None,
    ) -> UsageLog:
        """
        Log API usage event.

        Args:
            db: Database session
            tenant_id: Tenant ID
            action_type: Type of action (e.g., "post_generation", "meta_generation")
            tokens_used: Number of tokens consumed
            cost: Estimated cost in USD
            agent_id: Optional agent ID
            meta_data: Optional metadata (e.g., post_id, user_id)

        Returns:
            Created UsageLog entry
        """
        # Ensure meta_data includes cost
        full_meta = meta_data or {}
        if cost > 0:
            full_meta['cost_usd'] = cost

        usage_log = UsageLog(
            tenant_id=tenant_id,
            agent_id=agent_id,
            action=action_type,
            tokens_used=tokens_used,
            meta_data=full_meta,
        )

        db.add(usage_log)
        await db.flush()

        logger.info(
            f"Usage logged: tenant={tenant_id}, action={action_type}, "
            f"tokens={tokens_used}, cost=${cost:.4f}"
        )

        return usage_log

    @staticmethod
    async def update_tenant_usage(
        db: AsyncSession,
        tenant_id: UUID,
        tokens_delta: int = 0,
        posts_delta: int = 0,
    ) -> Tenant:
        """
        Update tenant usage counters.

        Args:
            db: Database session
            tenant_id: Tenant ID
            tokens_delta: Tokens to add to usage count
            posts_delta: Posts to add to usage count

        Returns:
            Updated Tenant

        Raises:
            ValueError: If tenant not found or quota exceeded
        """
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Update counters
        if tokens_delta > 0:
            # Check token limit
            if tenant.tokens_limit is not None:
                new_usage = tenant.tokens_used + tokens_delta
                if new_usage > tenant.tokens_limit:
                    raise ValueError(
                        f"Token limit exceeded. Limit: {tenant.tokens_limit}, "
                        f"Current: {tenant.tokens_used}, Requested: {tokens_delta}"
                    )
            tenant.tokens_used += tokens_delta

        if posts_delta > 0:
            # Check posts limit
            if tenant.posts_limit is not None:
                new_usage = tenant.posts_used + posts_delta
                if new_usage > tenant.posts_limit:
                    raise ValueError(
                        f"Posts limit exceeded. Limit: {tenant.posts_limit}, "
                        f"Current: {tenant.posts_used}, Requested: {posts_delta}"
                    )
            tenant.posts_used += posts_delta

        await db.flush()

        logger.info(
            f"Tenant usage updated: {tenant_id}, "
            f"tokens={tenant.tokens_used}/{tenant.tokens_limit}, "
            f"posts={tenant.posts_used}/{tenant.posts_limit}"
        )

        return tenant

    @staticmethod
    async def check_tenant_quota(
        db: AsyncSession,
        tenant_id: UUID,
        tokens_needed: int = 0,
        posts_needed: int = 0,
    ) -> dict:
        """
        Check if tenant has sufficient quota.

        Args:
            db: Database session
            tenant_id: Tenant ID
            tokens_needed: Tokens required for operation
            posts_needed: Posts required for operation

        Returns:
            Dictionary with availability status:
            {
                "tokens_available": bool,
                "posts_available": bool,
                "tokens_remaining": int | None,
                "posts_remaining": int | None,
            }
        """
        result = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        )
        tenant = result.scalar_one_or_none()

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Check tokens
        tokens_available = True
        tokens_remaining = None
        if tenant.tokens_limit is not None:
            tokens_remaining = tenant.tokens_limit - tenant.tokens_used
            tokens_available = tokens_remaining >= tokens_needed

        # Check posts
        posts_available = True
        posts_remaining = None
        if tenant.posts_limit is not None:
            posts_remaining = tenant.posts_limit - tenant.posts_used
            posts_available = posts_remaining >= posts_needed

        return {
            "tokens_available": tokens_available,
            "posts_available": posts_available,
            "tokens_remaining": tokens_remaining,
            "posts_remaining": posts_remaining,
        }


# Global instance
_usage_service: Optional[UsageService] = None


def get_usage_service() -> UsageService:
    """Get global usage service instance."""
    global _usage_service
    if _usage_service is None:
        _usage_service = UsageService()
    return _usage_service
