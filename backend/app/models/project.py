"""Projects, categories, tags, per-user permissions and favourites."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Table, Text, UniqueConstraint, Column,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import ProjectStatus, Visibility

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.suggestion import Suggestion
    from app.models.user import User

project_tags = Table(
    "project_tags",
    Base.metadata,
    Column("project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_project_tags_tag_id", "tag_id"),
)


class Category(Base, TimestampMixin):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255))
    icon: Mapped[str | None] = mapped_column(String(64))
    colour: Mapped[str | None] = mapped_column(String(24))
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    projects: Mapped[list["Project"]] = relationship(back_populates="category")


class Tag(Base, TimestampMixin):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(60), unique=True, nullable=False, index=True)

    projects: Mapped[list["Project"]] = relationship(
        secondary=project_tags, back_populates="tags"
    )


class Project(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "projects"
    __table_args__ = (
        Index("ix_projects_category_id", "category_id"),
        Index("ix_projects_status", "status"),
        Index("ix_projects_visibility", "visibility"),
        Index("ix_projects_active_deleted", "is_active", "is_deleted"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    short_description: Mapped[str | None] = mapped_column(String(280))
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    documentation_url: Mapped[str | None] = mapped_column(String(1024))
    # Source repository (GitHub or similar). Admin-only: surfaced in the admin
    # console, deliberately not on the employee-facing schemas.
    repository_url: Mapped[str | None] = mapped_column(String(1024))

    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"), nullable=True
    )
    category: Mapped[Category | None] = relationship(back_populates="projects", lazy="joined")

    tags: Mapped[list[Tag]] = relationship(
        secondary=project_tags, back_populates="projects", lazy="selectin"
    )

    owner_name: Mapped[str | None] = mapped_column(String(160))
    owner_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    icon: Mapped[str] = mapped_column(String(64), default="LayoutDashboard", nullable=False)
    colour: Mapped[str | None] = mapped_column(String(24))

    status: Mapped[str] = mapped_column(String(32), default=ProjectStatus.ACTIVE, nullable=False)
    visibility: Mapped[str] = mapped_column(
        String(32), default=Visibility.ALL_EMPLOYEES, nullable=False
    )
    allowed_departments: Mapped[str | None] = mapped_column(String(512))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    open_in_new_tab: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Denormalised counters, maintained by ProjectService on every open.
    total_opens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    permissions: Mapped[list["UserProjectPermission"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", lazy="selectin"
    )
    favourites: Mapped[list["Favourite"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    suggestions: Mapped[list["Suggestion"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    @property
    def department_list(self) -> list[str]:
        if not self.allowed_departments:
            return []
        return [d.strip() for d in self.allowed_departments.split(",") if d.strip()]


class UserProjectPermission(Base):
    """Explicit grant used when a project's visibility is SPECIFIC_EMPLOYEES."""

    __tablename__ = "user_project_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_user_project_permission"),
        Index("ix_upp_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    granted_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    project: Mapped[Project] = relationship(back_populates="permissions")
    user: Mapped["User"] = relationship(foreign_keys=[user_id], lazy="joined")


class Favourite(Base):
    __tablename__ = "favourites"
    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_favourite_user_project"),
        Index("ix_favourites_project_id", "project_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship(back_populates="favourites")
    project: Mapped[Project] = relationship(back_populates="favourites", lazy="joined")


class ProjectOpen(Base):
    """One row per launch. Powers 'recently opened' and usage analytics."""

    __tablename__ = "project_opens"
    __table_args__ = (
        Index("ix_project_opens_user_time", "user_id", "opened_at"),
        Index("ix_project_opens_project_time", "project_id", "opened_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
