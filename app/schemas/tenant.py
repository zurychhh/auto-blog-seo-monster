"""
Pydantic schemas for tenants.
"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class TenantCreate(BaseModel):
    """Create tenant schema."""
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=100, pattern="^[a-z0-9-]+$")
    tokens_limit: int = Field(default=100000, ge=0)
    posts_limit: int = Field(default=50, ge=0)
    settings: Optional[Dict[str, Any]] = None


class TenantUpdate(BaseModel):
    """Update tenant schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    is_active: Optional[bool] = None
    tokens_limit: Optional[int] = Field(None, ge=0)
    posts_limit: Optional[int] = Field(None, ge=0)
    settings: Optional[Dict[str, Any]] = None


class TenantResponse(BaseModel):
    """Tenant response schema."""
    id: UUID
    name: str
    slug: str
    is_active: bool
    tokens_limit: int
    tokens_used: int
    posts_limit: int
    posts_used: int
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TenantUsageResponse(BaseModel):
    """Tenant usage statistics."""
    tenant_id: UUID
    tokens_used: int
    tokens_limit: int
    tokens_percentage: float
    posts_used: int
    posts_limit: int
    posts_percentage: float
