"""Activity log and analytics schemas."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.common import ORMModel


class ActivityEntry(ORMModel):
    id: int
    user_id: int | None = None
    employee_id: str | None = None
    user_name: str | None = None
    event_type: str
    description: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    timestamp: datetime
    ip_address: str | None = None
    browser: str | None = None
    os: str | None = None
    device: str | None = None
    success: bool
    event_metadata: dict[str, Any] | None = None


class MyActivityEntry(ORMModel):
    """The user-facing view; IP and device are shown but nothing about others."""

    id: int
    event_type: str
    description: str | None = None
    project_id: int | None = None
    project_name: str | None = None
    timestamp: datetime
    ip_address: str | None = None
    browser: str | None = None
    device: str | None = None
    success: bool


class MostViewedProject(BaseModel):
    id: int
    name: str
    opens: int


class AnalyticsOverview(BaseModel):
    total_users: int
    active_users: int
    total_projects: int
    active_projects: int
    projects_added_this_month: int
    logins_today: int
    unique_active_users_today: int
    project_opens_today: int
    total_project_opens: int
    failed_logins_today: int
    activities_today: int
    locked_accounts: int
    most_viewed_project: MostViewedProject | None = None


class TimeSeriesPoint(BaseModel):
    date: str
    count: int


class ProjectUsageRow(BaseModel):
    project_id: int
    project_name: str
    opens: int
    unique_users: int


class CategoryBreakdownRow(BaseModel):
    category: str
    projects: int
    opens: int


class TopUserRow(BaseModel):
    user_id: int
    employee_id: str
    full_name: str
    department: str | None = None
    opens: int


class LoginTrends(BaseModel):
    successful_today: int
    successful_week: int
    successful_month: int
    failed_today: int
    failed_week: int
    failed_month: int


class AnalyticsResponse(BaseModel):
    overview: AnalyticsOverview
    daily_active_users: list[TimeSeriesPoint]
    daily_logins: list[TimeSeriesPoint]
    daily_project_opens: list[TimeSeriesPoint]
    project_usage: list[ProjectUsageRow]
    category_breakdown: list[CategoryBreakdownRow]
    top_users: list[TopUserRow]
    login_trends: LoginTrends


class ProjectUsageUser(BaseModel):
    employee_id: str
    full_name: str
    opens: int


class ProjectStatsResponse(BaseModel):
    project_id: int
    total_opens: int
    unique_users: int
    opens_in_period: int
    favourite_count: int
    last_opened_at: datetime | None = None
    daily_opens: list[TimeSeriesPoint]
    top_users: list[ProjectUsageUser]


class LoginHistoryEntry(ORMModel):
    id: int
    employee_id: str
    successful: bool
    failure_reason: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    attempted_at: datetime
