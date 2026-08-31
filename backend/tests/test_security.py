"""Input handling, injection resistance and audit-log immutability."""
import pytest
from sqlalchemy import select

from app.models.activity import ActivityLog
from app.models.user import User


@pytest.mark.parametrize(
    "payload",
    [
        "'; DROP TABLE users; --",
        "' OR '1'='1",
        "1; DELETE FROM projects",
        "%' UNION SELECT password_hash FROM users --",
    ],
)
def test_search_is_not_vulnerable_to_sql_injection(as_employee, db, project, payload):
    response = as_employee.get("/api/projects", params={"search": payload})
    assert response.status_code == 200
    assert response.json()["total"] == 0
    # Tables intact.
    assert db.execute(select(User)).scalars().first() is not None
    assert db.execute(select(ActivityLog)).scalars().first() is not None


def test_injection_in_login_is_handled_safely(client, db, employee):
    response = client.post(
        "/api/auth/login",
        json={"employee_id": "' OR 1=1 --", "password": "' OR 1=1 --"},
    )
    assert response.status_code == 401
    assert db.execute(select(User)).scalars().all()


def test_script_payload_is_stored_and_returned_verbatim_not_executed(as_admin, db):
    """The API must not interpret markup; it returns JSON, which the SPA escapes."""
    xss = "<script>alert('xss')</script>"
    created = as_admin.post(
        "/api/admin/projects",
        json={"name": f"Tool {xss}", "url": "https://example.internal/x"},
    )
    assert created.status_code == 201
    assert created.json()["name"] == f"Tool {xss}"
    assert created.headers["content-type"].startswith("application/json")
    assert created.headers["X-Content-Type-Options"] == "nosniff"


def test_oversized_input_is_rejected(as_admin):
    response = as_admin.post(
        "/api/admin/projects",
        json={"name": "A" * 500, "url": "https://example.internal/x"},
    )
    assert response.status_code == 422


def test_no_endpoint_exists_to_modify_the_audit_log(client):
    """Activity logs are append-only: no write route exists at all."""
    from app.main import app

    writable = [
        (route.path, sorted(route.methods))
        for route in app.routes
        if getattr(route, "methods", None)
        and "activity" in route.path
        and {"PUT", "PATCH", "DELETE"} & route.methods
    ]
    assert writable == []


def test_employee_cannot_delete_activity(as_employee):
    for path in ("/api/activity/me", "/api/admin/activity", "/api/admin/activity/1"):
        assert as_employee.delete(path).status_code in (401, 403, 404, 405)


def test_error_responses_do_not_leak_internals(client):
    response = client.get("/api/projects/999999")
    assert response.status_code == 401
    body = response.json()
    assert "Traceback" not in response.text
    assert set(body) == {"error", "message", "details"}


def test_health_endpoint_is_public_and_minimal(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert set(response.json()) == {"status", "database"}


def test_logs_do_not_contain_passwords(client, employee, caplog):
    import logging

    with caplog.at_level(logging.DEBUG):
        client.post(
            "/api/auth/login",
            json={"employee_id": employee.employee_id, "password": "SuperSecret123!"},
        )
    combined = "\n".join(record.getMessage() for record in caplog.records)
    assert "SuperSecret123!" not in combined
    assert "$argon2" not in combined
