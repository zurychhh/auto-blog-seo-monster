"""
Tenant model - represents a client/organization in multi-tenant system.
"""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, Integer, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class Tenant(Base):
    """Tenant model for multi-tenant isolation."""

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Limits
    tokens_limit: Mapped[int] = mapped_column(Integer, default=100000)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    posts_limit: Mapped[int] = mapped_column(Integer, default=50)
    posts_used: Mapped[int] = mapped_column(Integer, default=0)

    # Settings (JSON storage for flexible config)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    agents = relationship("Agent", back_populates="tenant", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="tenant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Tenant {self.name} ({self.slug})>"

    def has_tokens_available(self, required_tokens: int) -> bool:
        """Check if tenant has enough tokens."""
        return (self.tokens_used + required_tokens) <= self.tokens_limit

    def has_posts_available(self) -> bool:
        """Check if tenant can create more posts."""
        return self.posts_used < self.posts_limit
