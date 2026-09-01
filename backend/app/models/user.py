"""Users, roles and password history."""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin
from app.models.enums import AccountStatus, RoleName

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.models.project import Favourite


class Role(Base, TimestampMixin):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
    # Higher rank wins. USER=10, ADMIN=50, SUPER_ADMIN=100.
    rank: Mapped[int] = mapped_column(Integer, default=10, nullable=False)

    users: Mapped[list["User"]] = relationship(back_populates="role")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Role {self.name}>"


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"
    # Uniqueness applies to live accounts only. Deleting is a soft delete, so a
    # plain unique constraint would let a removed colleague keep hold of their
    # email address and employee ID forever, blocking a genuine re-hire or a
    # correction of a mistyped account. Users are never restored, so scoping the
    # constraint to non-deleted rows cannot resurrect a clash.
    __table_args__ = (
        Index(
            "ix_users_employee_id", "employee_id", unique=True,
            postgresql_where=text("is_deleted = false"),
            sqlite_where=text("is_deleted = 0"),
        ),
        Index(
            "uq_users_email_live", "email", unique=True,
            postgresql_where=text("is_deleted = false"),
            sqlite_where=text("is_deleted = 0"),
        ),
        Index("ix_users_department", "department"),
        Index("ix_users_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(64), nullable=False)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str | None] = mapped_column(String(120))
    job_title: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40))

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    role: Mapped[Role] = relationship(back_populates="users", lazy="joined")

    # Never serialised by any schema. See app/schemas/user.py.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default=AccountStatus.ACTIVE, nullable=False)

    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_by: Mapped["User | None"] = relationship(remote_side="User.id", lazy="selectin")
    notes: Mapped[str | None] = mapped_column(Text)

    favourites: Mapped[list["Favourite"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    sessions: Mapped[list["Session"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def role_name(self) -> str:
        return self.role.name if self.role else RoleName.USER

    @property
    def is_admin(self) -> bool:
        return self.role_name in (RoleName.ADMIN, RoleName.SUPER_ADMIN)

    @property
    def is_super_admin(self) -> bool:
        return self.role_name == RoleName.SUPER_ADMIN

    @property
    def can_login(self) -> bool:
        return (
            self.is_active
            and not self.is_deleted
            and self.status in (AccountStatus.ACTIVE, AccountStatus.PENDING_PASSWORD_CHANGE)
        )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<User {self.employee_id}>"


class PasswordHistory(Base):
    """Previous password hashes, to stop immediate reuse."""

    __tablename__ = "password_history"
    __table_args__ = (Index("ix_password_history_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    changed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )


class Session(Base):
    """Refresh-token sessions. The raw token is never stored, only its SHA-256."""

    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("refresh_token_hash", name="uq_sessions_refresh_token_hash"),
        Index("ix_sessions_user_active", "user_id", "revoked_at"),
        Index("ix_sessions_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))

    user: Mapped[User] = relationship(back_populates="sessions")


class LoginAttempt(Base):
    """Every authentication attempt, successful or not (rate limiting + forensics)."""

    __tablename__ = "login_attempts"
    __table_args__ = (
        Index("ix_login_attempts_employee_time", "employee_id", "attempted_at"),
        Index("ix_login_attempts_ip_time", "ip_address", "attempted_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[str] = mapped_column(String(64), nullable=False)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    successful: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    failure_reason: Mapped[str | None] = mapped_column(String(120))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
