"""
Pydantic schemas for schedule configuration.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class ScheduleIntervalEnum(str, Enum):
    """Available scheduling intervals."""
    DAILY = "daily"
    EVERY_3_DAYS = "every_3_days"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"


class PostLengthEnum(str, Enum):
    """Post length options."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"
    VERY_LONG = "very_long"


# ============ Request Schemas ============

class ScheduleCreate(BaseModel):
    """Schema for creating a new schedule."""

    agent_id: UUID = Field(..., description="Agent ID to associate with this schedule")

    interval: ScheduleIntervalEnum = Field(
        default=ScheduleIntervalEnum.WEEKLY,
        description="How often to generate posts"
    )

    publish_hour: int = Field(
        default=10,
        ge=0,
        le=23,
        description="Hour of day to publish (0-23, UTC)"
    )

    timezone: str = Field(
        default="Europe/Warsaw",
        description="Timezone for display purposes"
    )

    auto_publish: bool = Field(
        default=True,
        description="Auto-publish or save as draft"
    )

    target_keywords: Optional[List[str]] = Field(
        default=None,
        description="Preferred topics/keywords"
    )

    exclude_keywords: Optional[List[str]] = Field(
        default=None,
        description="Topics to avoid"
    )

    post_length: PostLengthEnum = Field(
        default=PostLengthEnum.LONG,
        description="Target post length"
    )

    is_active: bool = Field(
        default=True,
        description="Whether schedule is active"
    )

    @field_validator('target_keywords', 'exclude_keywords', mode='before')
    @classmethod
    def empty_list_to_none(cls, v):
        if v == []:
            return None
        return v


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule."""

    interval: Optional[ScheduleIntervalEnum] = None
    publish_hour: Optional[int] = Field(default=None, ge=0, le=23)
    timezone: Optional[str] = None
    auto_publish: Optional[bool] = None
    target_keywords: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None
    post_length: Optional[PostLengthEnum] = None
    is_active: Optional[bool] = None


# ============ Response Schemas ============

class ScheduleResponse(BaseModel):
    """Schema for schedule response."""

    id: UUID
    agent_id: UUID

    interval: str
    interval_display: str  # Human-readable in Polish
    publish_hour: int
    timezone: str
    cron_expression: str  # Generated cron

    is_active: bool
    auto_publish: bool

    target_keywords: Optional[List[str]]
    exclude_keywords: Optional[List[str]]
    post_length: str

    # Tracking
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]

    # Statistics
    total_posts_generated: int
    successful_posts: int
    failed_posts: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ScheduleListResponse(BaseModel):
    """Schema for list of schedules."""

    items: List[ScheduleResponse]
    total: int


class ScheduleRunResponse(BaseModel):
    """Schema for manual run response."""

    success: bool
    message: str
    task_id: Optional[str] = None
    post_id: Optional[str] = None


# ============ Statistics Schemas ============

class ScheduleStats(BaseModel):
    """Schedule statistics."""

    total_schedules: int
    active_schedules: int
    total_posts_generated: int
    successful_posts: int
    failed_posts: int
    success_rate: float

    posts_last_7_days: int
    posts_last_30_days: int

    upcoming_posts: List[dict]  # [{schedule_id, next_run_at, agent_name}]


# ============ Topic Discovery Schemas ============

class TrendingTopic(BaseModel):
    """Trending topic discovered by AI."""

    title: str
    category: str
    source: str
    source_url: Optional[str]
    discovered_at: datetime

    # SEO metrics (0-100 scale)
    search_volume_estimate: int = Field(ge=0, le=100)
    competition_level: str  # low, medium, high
    trending_score: float = Field(ge=0, le=1)

    # AI-generated suggestions
    suggested_keywords: List[str]
    suggested_title: str
    suggested_outline: Optional[List[str]]


class TopicDiscoveryRequest(BaseModel):
    """Request for topic discovery."""

    category: str = Field(
        default="prawo",
        description="Legal category to search"
    )
    count: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of topics to discover"
    )


class TopicDiscoveryResponse(BaseModel):
    """Response from topic discovery."""

    topics: List[TrendingTopic]
    discovered_at: datetime
    source_count: int
