"""Administrator audit and analytics endpoints."""
import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.auth.dependencies import AdminUser, Db
from app.database.base import utcnow
from app.models.activity import ActivityLog
from app.models.enums import EventType
from app.schemas.activity import (
    ActivityEntry, AnalyticsOverview, AnalyticsResponse, LoginHistoryEntry,
)
from app.schemas.common import Page
from app.services import activity_service, analytics_service

router = APIRouter(prefix="/admin", tags=["Admin - Activity"])


def _filters(
    employee_id: str | None,
    user_id: int | None,
    event_type: list[str] | None,
    project_id: int | None,
    success: bool | None,
    date_from: datetime | None,
    date_to: datetime | None,
    search: str | None,
) -> dict:
    return {
        "employee_id": employee_id,
        "user_id": user_id,
        "event_types": event_type,
        "project_id": project_id,
        "success": success,
        "date_from": date_from,
        "date_to": date_to,
        "search": search,
    }


@router.get("/activity", response_model=Page[ActivityEntry])
def list_activity(
    admin: AdminUser,
    db: Db,
    employee_id: Annotated[str | None, Query(max_length=64)] = None,
    user_id: int | None = None,
    event_type: Annotated[list[str] | None, Query()] = None,
    project_id: int | None = None,
    success: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ActivityEntry]:
    """The full audit trail across every employee."""
    rows, total = activity_service.query_activity(
        db,
        limit=limit,
        offset=offset,
        **_filters(employee_id, user_id, event_type, project_id, success, date_from, date_to, search),
    )
    return Page(
        items=[ActivityEntry.model_validate(r) for r in rows],
        total=total, limit=limit, offset=offset,
    )


@router.get("/activity/event-types", response_model=list[str])
def event_types(admin: AdminUser, db: Db) -> list[str]:
    """Known event types, with any historical values still present in the table."""
    used = {r[0] for r in db.execute(select(ActivityLog.event_type).distinct()).all()}
    return sorted(used | {str(e) for e in EventType})


@router.get("/activity/export")
def export_activity(
    admin: AdminUser,
    db: Db,
    employee_id: Annotated[str | None, Query(max_length=64)] = None,
    user_id: int | None = None,
    event_type: Annotated[list[str] | None, Query()] = None,
    project_id: int | None = None,
    success: bool | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    search: Annotated[str | None, Query(max_length=200)] = None,
    limit: Annotated[int, Query(ge=1, le=50000)] = 10000,
) -> StreamingResponse:
    """CSV export of the filtered audit trail."""
    rows, _ = activity_service.query_activity(
        db,
        limit=limit,
        offset=0,
        **_filters(employee_id, user_id, event_type, project_id, success, date_from, date_to, search),
    )

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Activity ID", "Timestamp (UTC)", "Employee ID", "Name", "Event Type",
        "Description", "Project ID", "Project", "Status", "IP Address",
        "Browser", "OS", "Device",
    ])
    for row in rows:
        writer.writerow([
            row.id,
            row.timestamp.strftime("%Y-%m-%d %H:%M:%S") if row.timestamp else "",
            row.employee_id or "",
            row.user_name or "",
            row.event_type,
            row.description or "",
            row.project_id or "",
            row.project_name or "",
            "Success" if row.success else "Failed",
            row.ip_address or "",
            row.browser or "",
            row.os or "",
            row.device or "",
        ])
    buffer.seek(0)
    filename = f"mf-ar-workstation-activity-{utcnow().strftime('%Y%m%d-%H%M%S')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/login-attempts", response_model=Page[LoginHistoryEntry])
def login_attempts(
    admin: AdminUser,
    db: Db,
    successful: bool | None = None,
    employee_id: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[LoginHistoryEntry]:
    from app.models.user import LoginAttempt

    stmt = select(LoginAttempt)
    if successful is not None:
        stmt = stmt.where(LoginAttempt.successful.is_(successful))
    if employee_id:
        stmt = stmt.where(func.lower(LoginAttempt.employee_id) == employee_id.strip().lower())

    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(LoginAttempt.attempted_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return Page(
        items=[LoginHistoryEntry.model_validate(r) for r in rows],
        total=total, limit=limit, offset=offset,
    )


@router.get("/analytics/overview", response_model=AnalyticsOverview)
def analytics_overview(admin: AdminUser, db: Db) -> AnalyticsOverview:
    return AnalyticsOverview(**analytics_service.overview(db))


@router.get("/analytics", response_model=AnalyticsResponse)
def analytics(
    admin: AdminUser,
    db: Db,
    days: Annotated[int, Query(ge=7, le=365)] = 30,
) -> AnalyticsResponse:
    """Every figure and series on the admin analytics page."""
    return AnalyticsResponse(
        overview=AnalyticsOverview(**analytics_service.overview(db)),
        daily_active_users=analytics_service.daily_active_users(db, days),
        daily_logins=analytics_service.daily_logins(db, days),
        daily_project_opens=analytics_service.daily_project_opens(db, days),
        project_usage=analytics_service.project_usage(db, days),
        category_breakdown=analytics_service.category_breakdown(db),
        top_users=analytics_service.top_users(db, days),
        login_trends=analytics_service.login_trends(db),
    )
