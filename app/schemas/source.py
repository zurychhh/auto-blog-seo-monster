"""
Pydantic schemas for knowledge sources.
"""

from pydantic import BaseModel, Field, HttpUrl
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class SourceCreate(BaseModel):
    """Create source schema."""
    type: str = Field(..., pattern="^(rss|scrape|search|sitemap|manual)$")
    name: str = Field(..., min_length=1, max_length=255)
    url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class SourceUpdate(BaseModel):
    """Update source schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class SourceResponse(BaseModel):
    """Source response schema."""
    id: UUID
    agent_id: UUID
    type: str
    name: str
    url: Optional[str]
    config: Dict[str, Any]
    is_active: bool
    last_fetched_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SourceTestRequest(BaseModel):
    """Test source connection request."""
    type: str
    url: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class SourceTestResponse(BaseModel):
    """Test source response."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
