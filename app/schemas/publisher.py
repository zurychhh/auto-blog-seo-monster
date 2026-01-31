"""
Pydantic schemas for publishers.
"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any


class PublisherCreate(BaseModel):
    """Create publisher schema."""
    type: str = Field(..., pattern="^(wordpress|ghost|ftp|webhook|github)$")
    name: str = Field(..., min_length=1, max_length=255)
    config: Dict[str, Any] = Field(..., description="Publisher-specific credentials and config")


class PublisherUpdate(BaseModel):
    """Update publisher schema."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class PublisherResponse(BaseModel):
    """Publisher response schema."""
    id: UUID
    agent_id: UUID
    type: str
    name: str
    config: Dict[str, Any]  # May want to mask sensitive fields in production
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PublisherTestRequest(BaseModel):
    """Test publisher connection request."""
    type: str
    config: Dict[str, Any]


class PublisherTestResponse(BaseModel):
    """Test publisher response."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
