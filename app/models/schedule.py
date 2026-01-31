"""
Schedule model - Automatic post scheduling configuration.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import Boolean, String, DateTime, Integer, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


class ScheduleInterval(str, Enum):
    """Available scheduling intervals."""
    DAILY = "daily"              # Every day
    EVERY_3_DAYS = "every_3_days"  # Every 3 days
    WEEKLY = "weekly"            # Once a week (Monday)
    BIWEEKLY = "biweekly"        # Every 2 weeks


# Mapping intervals to cron expressions
INTERVAL_CRON_MAP = {
    ScheduleInterval.DAILY: "0 {hour} * * *",           # Daily at specified hour
    ScheduleInterval.EVERY_3_DAYS: "0 {hour} */3 * *",  # Every 3 days
    ScheduleInterval.WEEKLY: "0 {hour} * * 1",          # Every Monday
    ScheduleInterval.BIWEEKLY: "0 {hour} 1,15 * *",     # 1st and 15th of month
}


class ScheduleConfig(Base):
    """Automatic post scheduling configuration."""

    __tablename__ = "schedule_configs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Link to agent
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Schedule configuration
    interval: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ScheduleInterval.WEEKLY.value
    )

    # Hour of publication (0-23, UTC)
    publish_hour: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=10  # 10:00 UTC = 11:00 CET
    )

    # Timezone for display (stored but cron runs in UTC)
    timezone: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="Europe/Warsaw"
    )

    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True
    )

    # Tracking
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # Auto-publish settings
    auto_publish: Mapped[bool] = mapped_column(
        Boolean,
        default=True,  # True = publish immediately, False = save as draft
    )

    # Content preferences
    target_keywords: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        default=list
    )

    exclude_keywords: Mapped[Optional[List[str]]] = mapped_column(
        ARRAY(String),
        nullable=True,
        default=list
    )

    # Post length preference
    post_length: Mapped[str] = mapped_column(
        String(50),
        default="long"  # short, medium, long, very_long
    )

    # Statistics
    total_posts_generated: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    successful_posts: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    failed_posts: Mapped[int] = mapped_column(
        Integer,
        default=0
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # Relationships
    agent = relationship("Agent", back_populates="schedule_configs")

    def __repr__(self):
        return f"<ScheduleConfig {self.id} - {self.interval} for agent {self.agent_id}>"

    def get_cron_expression(self) -> str:
        """Generate cron expression based on interval and publish hour."""
        template = INTERVAL_CRON_MAP.get(
            ScheduleInterval(self.interval),
            INTERVAL_CRON_MAP[ScheduleInterval.WEEKLY]
        )
        return template.format(hour=self.publish_hour)

    def get_interval_display(self) -> str:
        """Human-readable interval description in Polish."""
        displays = {
            ScheduleInterval.DAILY.value: "Codziennie",
            ScheduleInterval.EVERY_3_DAYS.value: "Co 3 dni",
            ScheduleInterval.WEEKLY.value: "Co tydzień",
            ScheduleInterval.BIWEEKLY.value: "Co 2 tygodnie",
        }
        return displays.get(self.interval, self.interval)
