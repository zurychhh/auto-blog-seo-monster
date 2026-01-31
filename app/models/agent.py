"""
Agent model - AI content generation expert.
"""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class Agent(Base):
    """AI Agent - expert for specific domain with persona and sources."""

    __tablename__ = "agents"

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
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    expertise: Mapped[str] = mapped_column(String(100), nullable=False)  # prawo, marketing, tech, etc.

    # AI Persona configuration
    persona: Mapped[str | None] = mapped_column(Text, nullable=True)  # Description of AI persona
    tone: Mapped[str] = mapped_column(String(50), default="professional")  # professional, casual, friendly, etc.
    post_length: Mapped[str] = mapped_column(String(50), default="medium")  # short, medium, long

    # Scheduling
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Cron expression

    # Workflow mode
    workflow: Mapped[str] = mapped_column(String(50), default="draft")  # auto, draft, scheduled

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Additional settings (JSON storage)
    settings: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    tenant = relationship("Tenant", back_populates="agents")
    sources = relationship("Source", back_populates="agent", cascade="all, delete-orphan")
    publishers = relationship("Publisher", back_populates="agent", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="agent", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="agent", cascade="all, delete-orphan")
    schedule_configs = relationship("ScheduleConfig", back_populates="agent", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Agent {self.name} - {self.expertise}>"

    def get_word_count_target(self) -> int:
        """Get target word count based on post_length setting."""
        targets = {
            "short": 500,
            "medium": 1000,
            "long": 2000,
            "very_long": 3000
        }
        return targets.get(self.post_length, 1000)
