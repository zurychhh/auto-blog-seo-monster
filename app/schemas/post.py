"""
Pydantic schemas for blog posts with SEO metadata.
"""

from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List


class PostCreate(BaseModel):
    """Create post schema - for manual post creation."""
    agent_id: UUID
    title: str = Field(..., min_length=1, max_length=500)
    slug: Optional[str] = None
    content: str = Field(..., min_length=1)
    excerpt: Optional[str] = None
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    keywords: Optional[List[str]] = None
    status: str = Field("draft", pattern="^(draft|scheduled|published)$")
    publisher_id: Optional[UUID] = None


class PostUpdate(BaseModel):
    """Update post schema."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    slug: Optional[str] = None
    content: Optional[str] = None
    excerpt: Optional[str] = None
    meta_title: Optional[str] = Field(None, max_length=70)
    meta_description: Optional[str] = Field(None, max_length=160)
    keywords: Optional[List[str]] = None
    schema_markup: Optional[Dict[str, Any]] = None
    og_image_url: Optional[str] = None
    canonical_url: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(draft|scheduled|published|failed)$")


class PostGenerateRequest(BaseModel):
    """Manual post generation request."""
    agent_id: UUID
    topic: Optional[str] = None  # Optional manual topic
    target_keyword: Optional[str] = None  # Optional target keyword for SEO


class PostPublishRequest(BaseModel):
    """Publish post request."""
    publisher_id: Optional[UUID] = None  # Use agent's default if not provided


class PostScheduleRequest(BaseModel):
    """Schedule post request."""
    scheduled_at: datetime
    publisher_id: Optional[UUID] = None


class PostResponse(BaseModel):
    """Post response schema."""
    id: UUID
    agent_id: UUID
    publisher_id: Optional[UUID]

    # Content
    title: str
    slug: Optional[str]
    content: str
    excerpt: Optional[str]

    # SEO
    meta_title: Optional[str]
    meta_description: Optional[str]
    keywords: List[str]
    schema_markup: Optional[Dict[str, Any]]
    og_image_url: Optional[str]
    canonical_url: Optional[str]

    # Stats
    readability_score: Optional[float]
    keyword_density: Optional[Dict[str, float]]
    word_count: Optional[int]

    # Workflow
    status: str
    scheduled_at: Optional[datetime]
    published_at: Optional[datetime]
    published_url: Optional[str]

    # AI metadata
    source_urls: List[str]
    tokens_used: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PostListResponse(BaseModel):
    """Paginated post list response."""
    items: List[PostResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SEOPreviewResponse(BaseModel):
    """SEO preview for SERP simulation."""
    meta_title: str
    meta_description: str
    url: str
    breadcrumbs: Optional[List[str]] = None
