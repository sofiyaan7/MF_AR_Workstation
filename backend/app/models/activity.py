"""Append-only business audit log."""
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.user import User


class ActivityLog(Base):
    """One row per auditable event.

    Written only through ActivityService; no API route exposes update or delete,
    so the table is effectively append-only for every caller including admins.
    """

    __tablename__ = "activity_logs"
    __table_args__ = (
        Index("ix_activity_logs_user_id", "user_id"),
        Index("ix_activity_logs_timestamp", "timestamp"),
        Index("ix_activity_logs_event_type", "event_type"),
        Index("ix_activity_logs_project_id", "project_id"),
        Index("ix_activity_logs_employee_id", "employee_id"),
        Index("ix_activity_logs_type_time", "event_type", "timestamp"),
        Index("ix_activity_logs_user_time", "user_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Nullable: a failed login for an unknown employee ID has no user row.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Denormalised so history survives a user being deleted.
    employee_id: Mapped[str | None] = mapped_column(String(64))
    user_name: Mapped[str | None] = mapped_column(String(160))

    event_type: Mapped[str] = mapped_column(String(48), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    project_name: Mapped[str | None] = mapped_column(String(160))

    target_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    device: Mapped[str | None] = mapped_column(String(80))
    browser: Mapped[str | None] = mapped_column(String(80))
    os: Mapped[str | None] = mapped_column(String(80))

    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User | None"] = relationship(foreign_keys=[user_id], lazy="joined")
