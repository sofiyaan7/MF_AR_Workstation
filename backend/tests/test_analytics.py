"""Admin analytics, audit querying and CSV export."""
import csv
import io

from tests.conftest import login


def test_analytics_reflects_real_activity(client, admin_user, employee, project):
    staff = login(client, employee.employee_id)
    staff.post(f"/api/projects/{project.id}/open")
    staff.post(f"/api/projects/{project.id}/open")
    staff.post("/api/auth/logout")
    client.post(
        "/api/auth/login", json={"employee_id": employee.employee_id, "password": "wrong"}
    )

    admin = login(client, admin_user.employee_id)
    overview = admin.get("/api/admin/analytics/overview").json()

    assert overview["total_users"] == 2
    assert overview["total_projects"] == 1
    assert overview["project_opens_today"] == 2
    assert overview["total_project_opens"] == 2
    assert overview["logins_today"] >= 2
    assert overview["failed_logins_today"] == 1
    assert overview["most_viewed_project"]["name"] == "MSCI Review Dashboard"
    assert overview["most_viewed_project"]["opens"] == 2


def test_full_analytics_payload_shape(as_admin, project):
    as_admin.post(f"/api/projects/{project.id}/open")
    body = as_admin.get("/api/admin/analytics?days=30").json()

    assert len(body["daily_active_users"]) == 30
    assert len(body["daily_logins"]) == 30
    assert len(body["daily_project_opens"]) == 30
    assert body["daily_project_opens"][-1]["count"] == 1  # today
    assert body["project_usage"][0]["project_name"] == "MSCI Review Dashboard"
    assert body["top_users"][0]["opens"] == 1
    assert body["login_trends"]["successful_today"] >= 1
    assert any(row["category"] == "Research" for row in body["category_breakdown"])


def test_analytics_starts_empty_with_no_fabricated_numbers(as_admin):
    body = as_admin.get("/api/admin/analytics").json()
    assert body["overview"]["total_project_opens"] == 0
    assert body["overview"]["most_viewed_project"] is None
    assert body["project_usage"] == []
    assert body["top_users"] == []
    assert all(point["count"] == 0 for point in body["daily_project_opens"])


def test_project_usage_stats(client, admin_user, employee, other_employee, project):
    for user in (employee, other_employee):
        api = login(client, user.employee_id)
        api.post(f"/api/projects/{project.id}/open")
        api.post("/api/auth/logout")

    admin = login(client, admin_user.employee_id)
    stats = admin.get(f"/api/admin/projects/{project.id}/stats?days=7").json()

    assert stats["total_opens"] == 2
    assert stats["unique_users"] == 2
    assert len(stats["daily_opens"]) == 7
    assert {u["employee_id"] for u in stats["top_users"]} == {
        employee.employee_id, other_employee.employee_id
    }


def test_activity_filters(client, admin_user, employee, project):
    staff = login(client, employee.employee_id)
    staff.post(f"/api/projects/{project.id}/open")
    staff.post(f"/api/projects/{project.id}/favourite")
    staff.post("/api/auth/logout")

    admin = login(client, admin_user.employee_id)
    assert admin.get("/api/admin/activity?event_type=PROJECT_OPENED").json()["total"] == 1
    assert admin.get(
        f"/api/admin/activity?employee_id={employee.employee_id}"
    ).json()["total"] >= 3
    assert admin.get(f"/api/admin/activity?project_id={project.id}").json()["total"] == 2
    assert admin.get("/api/admin/activity?success=false").json()["total"] == 0
    assert admin.get("/api/admin/activity?search=MSCI").json()["total"] >= 1


def test_activity_records_ip_and_browser(as_employee, project):
    as_employee.post(f"/api/projects/{project.id}/open")
    entry = as_employee.get("/api/activity/me").json()["items"][0]
    assert entry["ip_address"]
    assert entry["event_type"] == "PROJECT_OPENED"
    assert entry["project_name"] == "MSCI Review Dashboard"


def test_csv_export(client, admin_user, employee, project):
    staff = login(client, employee.employee_id)
    staff.post(f"/api/projects/{project.id}/open")
    staff.post("/api/auth/logout")

    admin = login(client, admin_user.employee_id)
    response = admin.get("/api/admin/activity/export")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment;" in response.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0][:5] == [
        "Activity ID", "Timestamp (UTC)", "Employee ID", "Name", "Event Type"
    ]
    assert len(rows) > 1
    assert any(row[4] == "PROJECT_OPENED" for row in rows[1:])


def test_csv_export_respects_filters(client, admin_user, employee, project):
    staff = login(client, employee.employee_id)
    staff.post(f"/api/projects/{project.id}/open")
    staff.post("/api/auth/logout")

    admin = login(client, admin_user.employee_id)
    response = admin.get("/api/admin/activity/export?event_type=PROJECT_OPENED")
    rows = list(csv.reader(io.StringIO(response.text)))[1:]
    assert len(rows) == 1


def test_login_attempts_endpoint_lists_failures(client, admin_user, employee):
    client.post(
        "/api/auth/login",
        json={"employee_id": employee.employee_id, "password": "Wrong1!Password"},
    )
    admin = login(client, admin_user.employee_id)
    body = admin.get("/api/admin/login-attempts?successful=false").json()
    assert body["total"] == 1
    assert body["items"][0]["failure_reason"] == "bad_password"


def test_admin_activity_answers_who_did_what(client, admin_user, employee, project):
    """The audit trail must attribute each action to a person and a time."""
    staff = login(client, employee.employee_id)
    staff.post(f"/api/projects/{project.id}/open")
    staff.post("/api/auth/logout")

    admin = login(client, admin_user.employee_id)
    entry = admin.get("/api/admin/activity?event_type=PROJECT_OPENED").json()["items"][0]
    assert entry["employee_id"] == employee.employee_id
    assert entry["user_name"] == "Sofiyaan Sameer"
    assert entry["project_name"] == "MSCI Review Dashboard"
    assert entry["timestamp"]
    assert entry["ip_address"]
    assert entry["success"] is True
