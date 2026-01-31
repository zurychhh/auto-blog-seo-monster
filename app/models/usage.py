"""
Usage tracking model - logs API usage, token consumption, etc.
"""

import uuid
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class UsageLog(Base):
    """Usage tracking for billing and monitoring."""

    __tablename__ = "usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Action type: generate, publish, fetch, etc.
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Token usage (for AI operations)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)

    # Additional metadata (renamed from 'metadata' to avoid SQLAlchemy conflict)
    meta_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    tenant = relationship("Tenant", back_populates="usage_logs")
    agent = relationship("Agent", back_populates="usage_logs")

    def __repr__(self):
        return f"<UsageLog {self.action} - {self.tokens_used} tokens>"
