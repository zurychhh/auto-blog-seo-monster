"""
Source model - knowledge sources for agents (RSS, scraping, search, etc.).
"""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class Source(Base):
    """Knowledge source for AI agents."""

    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Source type: rss, scrape, search, sitemap, manual
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)  # URL for RSS/scrape/sitemap

    # Adapter-specific configuration (JSON storage)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_fetched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="sources")

    def __repr__(self):
        return f"<Source {self.name} ({self.type})>"
