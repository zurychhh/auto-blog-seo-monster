"""
User model - authentication and authorization.
"""

import uuid
from datetime import datetime
from sqlalchemy import Boolean, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class User(Base):
    """User model with role-based access control."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,  # Superadmin has no tenant
        index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # superadmin, admin, editor
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="users")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"

    def is_superadmin(self) -> bool:
        """Check if user is superadmin."""
        return self.role == "superadmin"

    def is_admin(self) -> bool:
        """Check if user is admin."""
        return self.role == "admin"

    def is_editor(self) -> bool:
        """Check if user is editor."""
        return self.role == "editor"

    def has_role(self, required_role: str) -> bool:
        """Check if user has required role."""
        role_hierarchy = {"superadmin": 3, "admin": 2, "editor": 1}
        return role_hierarchy.get(self.role, 0) >= role_hierarchy.get(required_role, 0)
