"""Aggregations powering the admin analytics dashboard.

Every number here is computed from the database; there is no synthetic data.
"""
from datetime import datetime, timedelta

from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session as DbSession

from app.database.base import utcnow
from app.models.activity import ActivityLog
from app.models.enums import AccountStatus, EventType
from app.models.project import Category, Favourite, Project, ProjectOpen
from app.models.user import LoginAttempt, User
from app.services.activity_service import start_of_day_utc


def _day_expr(column):
    """Portable YYYY-MM-DD truncation (identical on PostgreSQL and SQLite)."""
    return func.substr(cast(column, String), 1, 10)


def overview(db: DbSession) -> dict:
    today = start_of_day_utc()
    month_start = today.replace(day=1)

    total_users = db.execute(
        select(func.count()).select_from(User).where(User.is_deleted.is_(False))
    ).scalar_one()
    active_users = db.execute(
        select(func.count())
        .select_from(User)
        .where(
            User.is_deleted.is_(False),
            User.is_active.is_(True),
            User.status == AccountStatus.ACTIVE,
        )
    ).scalar_one()
    total_projects = db.execute(
        select(func.count()).select_from(Project).where(Project.is_deleted.is_(False))
    ).scalar_one()
    active_projects = db.execute(
        select(func.count())
        .select_from(Project)
        .where(Project.is_deleted.is_(False), Project.is_active.is_(True))
    ).scalar_one()
    projects_this_month = db.execute(
        select(func.count())
        .select_from(Project)
        .where(Project.is_deleted.is_(False), Project.created_at >= month_start)
    ).scalar_one()
    logins_today = db.execute(
        select(func.count())
        .select_from(ActivityLog)
        .where(ActivityLog.event_type == EventType.LOGIN, ActivityLog.timestamp >= today)
    ).scalar_one()
    unique_users_today = db.execute(
        select(func.count(func.distinct(ActivityLog.user_id))).where(
            ActivityLog.timestamp >= today, ActivityLog.user_id.isnot(None)
        )
    ).scalar_one()
    opens_today = db.execute(
        select(func.count())
        .select_from(ProjectOpen)
        .where(ProjectOpen.opened_at >= today)
    ).scalar_one()
    total_opens = db.execute(select(func.count()).select_from(ProjectOpen)).scalar_one()
    failed_logins_today = db.execute(
        select(func.count())
        .select_from(LoginAttempt)
        .where(LoginAttempt.successful.is_(False), LoginAttempt.attempted_at >= today)
    ).scalar_one()
    activities_today = db.execute(
        select(func.count()).select_from(ActivityLog).where(ActivityLog.timestamp >= today)
    ).scalar_one()
    locked_accounts = db.execute(
        select(func.count())
        .select_from(User)
        .where(User.is_deleted.is_(False), User.locked_until.isnot(None), User.locked_until > utcnow())
    ).scalar_one()

    most_viewed_row = db.execute(
        select(Project.id, Project.name, Project.total_opens)
        .where(Project.is_deleted.is_(False))
        .order_by(Project.total_opens.desc())
        .limit(1)
    ).first()

    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_projects": total_projects,
        "active_projects": active_projects,
        "projects_added_this_month": projects_this_month,
        "logins_today": logins_today,
        "unique_active_users_today": unique_users_today,
        "project_opens_today": opens_today,
        "total_project_opens": total_opens,
        "failed_logins_today": failed_logins_today,
        "activities_today": activities_today,
        "locked_accounts": locked_accounts,
        "most_viewed_project": (
            {"id": most_viewed_row[0], "name": most_viewed_row[1], "opens": most_viewed_row[2]}
            if most_viewed_row and most_viewed_row[2]
            else None
        ),
    }


def _fill_series(rows: list[tuple[str, int]], days: int) -> list[dict]:
    """Return one entry per day so charts have no gaps."""
    counts = {r[0]: r[1] for r in rows}
    start = start_of_day_utc() - timedelta(days=days - 1)
    return [
        {
            "date": (start + timedelta(days=i)).strftime("%Y-%m-%d"),
            "count": counts.get((start + timedelta(days=i)).strftime("%Y-%m-%d"), 0),
        }
        for i in range(days)
    ]


def daily_active_users(db: DbSession, days: int = 30) -> list[dict]:
    since = start_of_day_utc() - timedelta(days=days - 1)
    day = _day_expr(ActivityLog.timestamp)
    rows = db.execute(
        select(day.label("d"), func.count(func.distinct(ActivityLog.user_id)))
        .where(ActivityLog.timestamp >= since, ActivityLog.user_id.isnot(None))
        .group_by("d")
        .order_by("d")
    ).all()
    return _fill_series([(r[0], r[1]) for r in rows], days)


def daily_logins(db: DbSession, days: int = 30) -> list[dict]:
    since = start_of_day_utc() - timedelta(days=days - 1)
    day = _day_expr(ActivityLog.timestamp)
    rows = db.execute(
        select(day.label("d"), func.count(ActivityLog.id))
        .where(ActivityLog.timestamp >= since, ActivityLog.event_type == EventType.LOGIN)
        .group_by("d")
        .order_by("d")
    ).all()
    return _fill_series([(r[0], r[1]) for r in rows], days)


def daily_project_opens(db: DbSession, days: int = 30) -> list[dict]:
    since = start_of_day_utc() - timedelta(days=days - 1)
    day = _day_expr(ProjectOpen.opened_at)
    rows = db.execute(
        select(day.label("d"), func.count(ProjectOpen.id))
        .where(ProjectOpen.opened_at >= since)
        .group_by("d")
        .order_by("d")
    ).all()
    return _fill_series([(r[0], r[1]) for r in rows], days)


def project_usage(db: DbSession, days: int = 30, limit: int = 10) -> list[dict]:
    since = start_of_day_utc() - timedelta(days=days - 1)
    rows = db.execute(
        select(
            Project.id,
            Project.name,
            func.count(ProjectOpen.id).label("opens"),
            func.count(func.distinct(ProjectOpen.user_id)).label("unique_users"),
        )
        .join(ProjectOpen, ProjectOpen.project_id == Project.id)
        .where(ProjectOpen.opened_at >= since, Project.is_deleted.is_(False))
        .group_by(Project.id, Project.name)
        .order_by(func.count(ProjectOpen.id).desc())
        .limit(limit)
    ).all()
    return [
        {"project_id": r[0], "project_name": r[1], "opens": r[2], "unique_users": r[3]}
        for r in rows
    ]


def category_breakdown(db: DbSession) -> list[dict]:
    rows = db.execute(
        select(
            func.coalesce(Category.name, "Uncategorised"),
            func.count(Project.id),
            func.coalesce(func.sum(Project.total_opens), 0),
        )
        .select_from(Project)
        .outerjoin(Category, Project.category_id == Category.id)
        .where(Project.is_deleted.is_(False))
        .group_by(Category.name)
        .order_by(func.count(Project.id).desc())
    ).all()
    return [{"category": r[0], "projects": r[1], "opens": int(r[2] or 0)} for r in rows]


def top_users(db: DbSession, days: int = 30, limit: int = 10) -> list[dict]:
    since = start_of_day_utc() - timedelta(days=days - 1)
    rows = db.execute(
        select(
            User.id,
            User.employee_id,
            User.full_name,
            User.department,
            func.count(ProjectOpen.id).label("opens"),
        )
        .join(ProjectOpen, ProjectOpen.user_id == User.id)
        .where(ProjectOpen.opened_at >= since)
        .group_by(User.id, User.employee_id, User.full_name, User.department)
        .order_by(func.count(ProjectOpen.id).desc())
        .limit(limit)
    ).all()
    return [
        {
            "user_id": r[0],
            "employee_id": r[1],
            "full_name": r[2],
            "department": r[3],
            "opens": r[4],
        }
        for r in rows
    ]


def project_stats(db: DbSession, project_id: int, days: int = 30) -> dict:
    since = start_of_day_utc() - timedelta(days=days - 1)

    total_opens = db.execute(
        select(func.count()).select_from(ProjectOpen).where(ProjectOpen.project_id == project_id)
    ).scalar_one()
    unique_users = db.execute(
        select(func.count(func.distinct(ProjectOpen.user_id))).where(
            ProjectOpen.project_id == project_id
        )
    ).scalar_one()
    opens_in_period = db.execute(
        select(func.count())
        .select_from(ProjectOpen)
        .where(ProjectOpen.project_id == project_id, ProjectOpen.opened_at >= since)
    ).scalar_one()
    last_opened = db.execute(
        select(func.max(ProjectOpen.opened_at)).where(ProjectOpen.project_id == project_id)
    ).scalar_one()
    favourites = db.execute(
        select(func.count()).select_from(Favourite).where(Favourite.project_id == project_id)
    ).scalar_one()

    day = _day_expr(ProjectOpen.opened_at)
    series_rows = db.execute(
        select(day.label("d"), func.count(ProjectOpen.id))
        .where(ProjectOpen.project_id == project_id, ProjectOpen.opened_at >= since)
        .group_by("d")
        .order_by("d")
    ).all()

    user_rows = db.execute(
        select(User.employee_id, User.full_name, func.count(ProjectOpen.id))
        .join(User, User.id == ProjectOpen.user_id)
        .where(ProjectOpen.project_id == project_id)
        .group_by(User.employee_id, User.full_name)
        .order_by(func.count(ProjectOpen.id).desc())
        .limit(10)
    ).all()

    return {
        "project_id": project_id,
        "total_opens": total_opens,
        "unique_users": unique_users,
        "opens_in_period": opens_in_period,
        "favourite_count": favourites,
        "last_opened_at": last_opened,
        "daily_opens": _fill_series([(r[0], r[1]) for r in series_rows], days),
        "top_users": [
            {"employee_id": r[0], "full_name": r[1], "opens": r[2]} for r in user_rows
        ],
    }


def login_trends(db: DbSession) -> dict:
    now = utcnow()
    def count_since(since: datetime, successful: bool) -> int:
        return db.execute(
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.attempted_at >= since,
                LoginAttempt.successful.is_(successful),
            )
        ).scalar_one()

    return {
        "successful_today": count_since(start_of_day_utc(), True),
        "successful_week": count_since(now - timedelta(days=7), True),
        "successful_month": count_since(now - timedelta(days=30), True),
        "failed_today": count_since(start_of_day_utc(), False),
        "failed_week": count_since(now - timedelta(days=7), False),
        "failed_month": count_since(now - timedelta(days=30), False),
    }
