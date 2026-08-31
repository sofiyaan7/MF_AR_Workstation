"""Business audit logging.

This is the only write path into ``activity_logs``. There is intentionally no
update or delete function anywhere in the codebase, so the table is
append-only for every caller including administrators.
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session as DbSession

from app.database.base import utcnow
from app.models.activity import ActivityLog
from app.models.enums import EventType
from app.models.project import Project
from app.models.user import User
from app.utils.request_context import RequestContext


def record_activity(
    db: DbSession,
    *,
    event_type: EventType | str,
    user: User | None = None,
    employee_id: str | None = None,
    user_name: str | None = None,
    description: str | None = None,
    project: Project | None = None,
    project_id: int | None = None,
    project_name: str | None = None,
    target_user_id: int | None = None,
    success: bool = True,
    context: RequestContext | None = None,
    metadata: dict[str, Any] | None = None,
    commit: bool = False,
) -> ActivityLog:
    """Append one audit row.

    Pass ``commit=True`` when the caller is about to raise: the request-scoped
    session is rolled back by the error handler, which would otherwise discard
    the very event being recorded (a denied access, a rejected password change).
    """
    entry = ActivityLog(
        user_id=user.id if user else None,
        employee_id=(user.employee_id if user else employee_id),
        user_name=(user.full_name if user else user_name),
        event_type=str(event_type),
        description=description,
        project_id=project.id if project else project_id,
        project_name=project.name if project else project_name,
        target_user_id=target_user_id,
        timestamp=utcnow(),
        ip_address=context.ip_address if context else None,
        user_agent=context.user_agent if context else None,
        device=context.device if context else None,
        browser=context.browser if context else None,
        os=context.os if context else None,
        success=success,
        event_metadata=metadata,
    )
    db.add(entry)
    db.flush()
    if commit:
        db.commit()
    return entry


def _base_query() -> Select:
    return select(ActivityLog).order_by(ActivityLog.timestamp.desc(), ActivityLog.id.desc())


def query_activity(
    db: DbSession,
    *,
    user_id: int | None = None,
    employee_id: str | None = None,
    event_types: Sequence[str] | None = None,
    project_id: int | None = None,
    success: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ActivityLog], int]:
    """Filtered, paginated audit query. Returns ``(rows, total_matching)``."""
    filters = []
    if user_id is not None:
        filters.append(ActivityLog.user_id == user_id)
    if employee_id:
        filters.append(ActivityLog.employee_id == employee_id)
    if event_types:
        filters.append(ActivityLog.event_type.in_([str(e) for e in event_types]))
    if project_id is not None:
        filters.append(ActivityLog.project_id == project_id)
    if success is not None:
        filters.append(ActivityLog.success.is_(success))
    if date_from is not None:
        filters.append(ActivityLog.timestamp >= date_from)
    if date_to is not None:
        filters.append(ActivityLog.timestamp <= date_to)
    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            ActivityLog.description.ilike(pattern)
            | ActivityLog.user_name.ilike(pattern)
            | ActivityLog.employee_id.ilike(pattern)
            | ActivityLog.project_name.ilike(pattern)
        )

    stmt = _base_query()
    count_stmt = select(func.count()).select_from(ActivityLog)
    for f in filters:
        stmt = stmt.where(f)
        count_stmt = count_stmt.where(f)

    total = db.execute(count_stmt).scalar_one()
    rows = list(db.execute(stmt.limit(limit).offset(offset)).scalars().unique())
    return rows, total


def touch_last_activity(db: DbSession, user: User) -> None:
    user.last_activity_at = utcnow()
    db.add(user)


def start_of_day_utc(reference: datetime | None = None) -> datetime:
    ref = reference or utcnow()
    return ref.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def days_ago(days: int) -> datetime:
    return start_of_day_utc() - timedelta(days=days)
