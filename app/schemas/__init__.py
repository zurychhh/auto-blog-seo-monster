"""
Pydantic schemas - import all schemas for easier access.
"""

from app.schemas.auth import (
    UserLogin,
    UserRegister,
    Token,
    TokenData,
    UserResponse,
)
from app.schemas.tenant import (
    TenantCreate,
    TenantUpdate,
    TenantResponse,
    TenantUsageResponse,
)
from app.schemas.agent import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    AgentRunRequest,
)
from app.schemas.source import (
    SourceCreate,
    SourceUpdate,
    SourceResponse,
    SourceTestRequest,
    SourceTestResponse,
)
from app.schemas.publisher import (
    PublisherCreate,
    PublisherUpdate,
    PublisherResponse,
    PublisherTestRequest,
    PublisherTestResponse,
)
from app.schemas.post import (
    PostCreate,
    PostUpdate,
    PostGenerateRequest,
    PostPublishRequest,
    PostScheduleRequest,
    PostResponse,
    PostListResponse,
    SEOPreviewResponse,
)
from app.schemas.schedule import (
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleResponse,
    ScheduleListResponse,
    ScheduleRunResponse,
    ScheduleStats,
    TrendingTopic,
    TopicDiscoveryRequest,
    TopicDiscoveryResponse,
)

__all__ = [
    # Auth
    "UserLogin",
    "UserRegister",
    "Token",
    "TokenData",
    "UserResponse",
    # Tenant
    "TenantCreate",
    "TenantUpdate",
    "TenantResponse",
    "TenantUsageResponse",
    # Agent
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    "AgentRunRequest",
    # Source
    "SourceCreate",
    "SourceUpdate",
    "SourceResponse",
    "SourceTestRequest",
    "SourceTestResponse",
    # Publisher
    "PublisherCreate",
    "PublisherUpdate",
    "PublisherResponse",
    "PublisherTestRequest",
    "PublisherTestResponse",
    # Post
    "PostCreate",
    "PostUpdate",
    "PostGenerateRequest",
    "PostPublishRequest",
    "PostScheduleRequest",
    "PostResponse",
    "PostListResponse",
    "SEOPreviewResponse",
    # Schedule
    "ScheduleCreate",
    "ScheduleUpdate",
    "ScheduleResponse",
    "ScheduleListResponse",
    "ScheduleRunResponse",
    "ScheduleStats",
    "TrendingTopic",
    "TopicDiscoveryRequest",
    "TopicDiscoveryResponse",
]
