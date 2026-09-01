"""Server-side authorization.

These tests call the admin endpoints directly as a normal employee, which is
exactly what a user who bypasses the UI would do.
"""
import pytest
from sqlalchemy import select

from app.models.activity import ActivityLog
from app.models.enums import EventType
from tests.conftest import login

ADMIN_GET_ENDPOINTS = [
    "/api/admin/users",
    "/api/admin/users/departments",
    "/api/admin/projects",
    "/api/admin/categories",
    "/api/admin/activity",
    "/api/admin/activity/event-types",
    "/api/admin/activity/export",
    "/api/admin/analytics",
    "/api/admin/analytics/overview",
    "/api/admin/login-attempts",
]


@pytest.mark.parametrize("endpoint", ADMIN_GET_ENDPOINTS)
def test_employee_cannot_read_admin_endpoints(as_employee, endpoint):
    response = as_employee.get(endpoint)
    assert response.status_code == 403, f"{endpoint} leaked to a normal employee"


@pytest.mark.parametrize("endpoint", ADMIN_GET_ENDPOINTS)
def test_anonymous_cannot_read_admin_endpoints(client, endpoint):
    assert client.get(endpoint).status_code == 401


def test_employee_cannot_create_a_user(as_employee):
    response = as_employee.post(
        "/api/admin/users",
        json={
            "employee_id": "HACK001",
            "full_name": "Injected Account",
            "email": "hack@example.com",
            "role": "ADMIN",
        },
    )
    assert response.status_code == 403


def test_employee_cannot_create_a_project(as_employee, category):
    response = as_employee.post(
        "/api/admin/projects",
        json={"name": "Rogue Project", "url": "https://example.com"},
    )
    assert response.status_code == 403


def test_employee_cannot_update_or_delete_a_project(as_employee, project):
    assert as_employee.put(
        f"/api/admin/projects/{project.id}", json={"name": "Renamed"}
    ).status_code == 403
    assert as_employee.delete(f"/api/admin/projects/{project.id}").status_code == 403


def test_employee_cannot_disable_another_user(as_employee, other_employee):
    assert as_employee.post(
        f"/api/admin/users/{other_employee.id}/disable"
    ).status_code == 403


def test_employee_cannot_reset_another_users_password(as_employee, other_employee):
    assert as_employee.post(
        f"/api/admin/users/{other_employee.id}/reset-password"
    ).status_code == 403


def test_employee_cannot_read_another_users_activity(as_employee, other_employee):
    assert as_employee.get(
        f"/api/admin/users/{other_employee.id}/activity"
    ).status_code == 403


def test_my_activity_only_returns_own_events(client, db, employee, other_employee, project):
    """Two users act; each must see only their own history."""
    mine = login(client, employee.full_name)
    mine.post(f"/api/projects/{project.id}/open")
    mine.post("/api/auth/logout")

    theirs = login(client, other_employee.full_name)
    theirs.post(f"/api/projects/{project.id}/open")

    response = theirs.get("/api/activity/me")
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    # Nothing in the payload belongs to the other employee.
    assert employee.full_name not in response.text
    assert "ARWL12345" not in response.text

    owner_ids = {
        db.get(ActivityLog, item["id"]).user_id for item in items
    }
    assert owner_ids == {other_employee.id}


def test_my_activity_ignores_a_user_id_supplied_by_the_client(
    client, employee, other_employee, project
):
    """A crafted query parameter must not widen the scope."""
    theirs = login(client, other_employee.full_name)
    theirs.post(f"/api/projects/{project.id}/open")
    theirs.post("/api/auth/logout")

    mine = login(client, employee.full_name)
    response = mine.get(f"/api/activity/me?user_id={other_employee.id}&employee_id=ARWL12346")
    assert response.status_code == 200
    assert other_employee.full_name not in response.text


def test_denied_admin_access_is_audited(as_employee, db, employee):
    as_employee.get("/api/admin/users")
    logs = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.UNAUTHORIZED_ACCESS)
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].user_id == employee.id
    assert logs[0].success is False


def test_plain_admin_cannot_modify_a_super_admin(client, plain_admin, admin_user):
    api = login(client, plain_admin.full_name)
    response = api.put(f"/api/admin/users/{admin_user.id}", json={"role": "USER"})
    assert response.status_code == 403
    assert "super administrator" in response.json()["message"].lower()


def test_plain_admin_cannot_create_a_super_admin(client, plain_admin):
    api = login(client, plain_admin.full_name)
    response = api.post(
        "/api/admin/users",
        json={
            "employee_id": "SUPER999",
            "full_name": "Escalated Admin",
            "email": "super999@example.com",
            "role": "SUPER_ADMIN",
        },
    )
    assert response.status_code == 403


def test_admin_cannot_disable_their_own_account(as_admin, admin_user):
    response = as_admin.post(f"/api/admin/users/{admin_user.id}/disable")
    assert response.status_code == 403
    assert "your own account" in response.json()["message"]


def test_admin_can_reach_admin_endpoints(as_admin):
    for endpoint in ADMIN_GET_ENDPOINTS:
        assert as_admin.get(endpoint).status_code == 200, endpoint


def test_disabled_user_token_stops_working_immediately(client, db, employee, admin_user):
    """A live session must die the moment the account is disabled."""
    victim = login(client, employee.full_name)
    assert victim.get("/api/auth/me").status_code == 200
    victim_csrf = victim.csrf
    victim_cookies = dict(client.cookies)

    client.cookies.clear()
    admin = login(client, admin_user.full_name)
    assert admin.post(f"/api/admin/users/{employee.id}/disable").status_code == 200

    client.cookies.clear()
    for name, value in victim_cookies.items():
        client.cookies.set(name, value)
    response = client.get("/api/auth/me", headers={"X-CSRF-Token": victim_csrf})
    assert response.status_code == 401
