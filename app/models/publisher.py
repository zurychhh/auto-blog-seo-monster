"""
Publisher model - publication destinations (WordPress, Ghost, FTP, etc.).
"""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class Publisher(Base):
    """Publication destination for posts."""

    __tablename__ = "publishers"

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

    # Publisher type: wordpress, ghost, ftp, webhook, github
    type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Publisher-specific configuration (credentials, endpoints)
    # Example for WordPress: {"url": "...", "username": "...", "password": "..."}
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    agent = relationship("Agent", back_populates="publishers")
    posts = relationship("Post", back_populates="publisher")

    def __repr__(self):
        return f"<Publisher {self.name} ({self.type})>"
