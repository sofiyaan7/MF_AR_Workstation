"""Per-project change suggestions raised by any employee."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin
from app.models.enums import SuggestionStatus

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Project
    from app.models.user import User


class Suggestion(Base, TimestampMixin):
    """A change request against a project.

    Deliberately visible to every employee who can see the project: the point
    is a shared, auditable log of what has been asked for and what has been
    dealt with, not a private inbox. Rows are never deleted — closing sets the
    status so the history survives.
    """

    __tablename__ = "suggestions"
    __table_args__ = (
        Index("ix_suggestions_project_id", "project_id"),
        Index("ix_suggestions_status", "status"),
        Index("ix_suggestions_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    project: Mapped["Project"] = relationship(back_populates="suggestions")

    # SET NULL, not CASCADE: a suggestion outlives the account that raised it,
    # otherwise deleting a leaver would silently rewrite the project's history.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user: Mapped["User | None"] = relationship(foreign_keys=[user_id], lazy="joined")

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)

    status: Mapped[str] = mapped_column(
        String(32), default=str(SuggestionStatus.OPEN), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    closed_by: Mapped["User | None"] = relationship(foreign_keys=[closed_by_id], lazy="joined")

    @property
    def is_open(self) -> bool:
        return self.status == str(SuggestionStatus.OPEN)
