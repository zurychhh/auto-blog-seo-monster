"""
Post model - generated blog posts with SEO metadata.
"""

import uuid
from datetime import datetime
from sqlalchemy import Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class Post(Base):
    """Blog post with full SEO metadata."""

    __tablename__ = "posts"

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
    publisher_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("publishers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Content
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown or HTML
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)

    # SEO Metadata
    meta_title: Mapped[str | None] = mapped_column(String(70), nullable=True)  # Max 60-70 chars
    meta_description: Mapped[str | None] = mapped_column(String(160), nullable=True)  # Max 160 chars
    keywords: Mapped[list] = mapped_column(JSONB, default=list)  # List of keywords
    schema_markup: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # JSON-LD schema
    og_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stats
    readability_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # Flesch-Kincaid
    keyword_density: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # Keyword -> density %
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Workflow
    status: Mapped[str] = mapped_column(String(50), default="draft", index=True)  # draft, scheduled, published, failed
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    published_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # Final URL after publish

    # AI Metadata
    source_urls: Mapped[list] = mapped_column(JSONB, default=list)  # List of source URLs
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)  # Prompt used

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    agent = relationship("Agent", back_populates="posts")
    publisher = relationship("Publisher", back_populates="posts")

    def __repr__(self):
        return f"<Post {self.title} ({self.status})>"

    def is_published(self) -> bool:
        """Check if post is published."""
        return self.status == "published"

    def is_draft(self) -> bool:
        """Check if post is draft."""
        return self.status == "draft"

    def is_scheduled(self) -> bool:
        """Check if post is scheduled."""
        return self.status == "scheduled"
