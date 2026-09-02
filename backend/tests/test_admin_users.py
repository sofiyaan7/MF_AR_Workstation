"""Administrator user management and the employee lifecycle."""
from sqlalchemy import select

from app.models.activity import ActivityLog
from app.models.enums import EventType
from app.models.user import User
from tests.conftest import TEST_PASSWORD, login


def _create_employee(api, **overrides) -> dict:
    payload = {
        "employee_id": "ARWL77777",
        "full_name": "New Joiner",
        "email": "new.joiner@example.com",
        "department": "Research",
        "role": "USER",
        "status": "ACTIVE",
    }
    payload.update(overrides)
    response = api.post("/api/admin/users", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_admin_creates_employee_who_can_then_log_in(client, admin_user):
    admin = login(client, admin_user.full_name)
    body = _create_employee(admin)
    temp_password = body["temporary_password"]
    assert temp_password, "a temporary password should be issued and shown once"
    assert body["user"]["employee_id"] == "ARWL77777"
    assert body["user"]["role"] == "USER"
    admin.post("/api/auth/logout")

    response = client.post(
        "/api/auth/login",
        json={"username": "New Joiner", "password": temp_password},
    )
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


def test_new_employee_must_change_password_before_using_the_portal(client, admin_user):
    admin = login(client, admin_user.full_name)
    body = _create_employee(admin)
    admin.post("/api/auth/logout")

    api = login(client, "New Joiner", body["temporary_password"])
    # Blocked from normal use...
    assert api.get("/api/projects").status_code == 403
    # ...but able to set a new password.
    new_password = "MyOwnP@ssword77"
    assert api.post(
        "/api/auth/change-password",
        json={
            "current_password": body["temporary_password"],
            "new_password": new_password,
            "confirm_password": new_password,
        },
    ).status_code == 200
    assert api.get("/api/projects").status_code == 200


def test_employee_id_must_be_unique(as_admin, employee):
    response = as_admin.post(
        "/api/admin/users",
        json={
            "employee_id": employee.employee_id,
            "full_name": "Impostor",
            "email": "impostor@example.com",
        },
    )
    assert response.status_code == 409


def test_email_must_be_unique(as_admin, employee):
    response = as_admin.post(
        "/api/admin/users",
        json={
            "employee_id": "ARWL88888",
            "full_name": "Duplicate Email",
            "email": employee.email,
        },
    )
    assert response.status_code == 409


def test_admin_supplied_temporary_password_must_meet_policy(as_admin):
    response = as_admin.post(
        "/api/admin/users",
        json={
            "employee_id": "ARWL66666",
            "full_name": "Weak Password",
            "email": "weak@example.com",
            "temporary_password": "abc",
        },
    )
    assert response.status_code == 422


def test_user_creation_is_audited(as_admin, db, admin_user):
    _create_employee(as_admin)
    log = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.USER_CREATED)
    ).scalars().one()
    assert log.user_id == admin_user.id
    assert "ARWL77777" in log.description


def test_admin_can_edit_an_employee(as_admin, employee):
    response = as_admin.put(
        f"/api/admin/users/{employee.id}",
        json={"department": "Portfolio", "job_title": "Senior Analyst"},
    )
    assert response.status_code == 200
    assert response.json()["department"] == "Portfolio"
    assert response.json()["job_title"] == "Senior Analyst"


def test_admin_can_change_a_role(as_admin, db, employee):
    response = as_admin.put(f"/api/admin/users/{employee.id}", json={"role": "ADMIN"})
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"

    log = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.ROLE_CHANGED)
    ).scalars().one()
    assert "USER -> ADMIN" in log.description


def test_promoted_user_gains_admin_access(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    admin.put(f"/api/admin/users/{employee.id}", json={"role": "ADMIN"})
    admin.post("/api/auth/logout")

    promoted = login(client, employee.full_name)
    assert promoted.get("/api/admin/users").status_code == 200


def test_disable_then_enable_an_employee(client, db, admin_user, employee):
    admin = login(client, admin_user.full_name)
    assert admin.post(f"/api/admin/users/{employee.id}/disable").status_code == 200

    db.expire_all()
    assert db.get(User, employee.id).is_active is False
    assert client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": TEST_PASSWORD},
    ).status_code == 401

    assert admin.post(f"/api/admin/users/{employee.id}/enable").status_code == 200
    admin.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": TEST_PASSWORD},
    ).status_code == 200


def test_disable_is_audited(as_admin, db, employee):
    as_admin.post(f"/api/admin/users/{employee.id}/disable")
    log = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.USER_DISABLED)
    ).scalars().first()
    assert log is not None and log.target_user_id == employee.id


def test_admin_reset_password_issues_a_working_temporary_password(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    response = admin.post(f"/api/admin/users/{employee.id}/reset-password")
    assert response.status_code == 200
    temp_password = response.json()["temporary_password"]
    admin.post("/api/auth/logout")

    # The old password no longer works; the new one does.
    assert client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": TEST_PASSWORD},
    ).status_code == 401
    login_response = client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": temp_password},
    )
    assert login_response.status_code == 200
    assert login_response.json()["must_change_password"] is True


def test_reset_password_revokes_existing_sessions(client, admin_user, employee):
    login(client, employee.full_name)
    victim_cookies = dict(client.cookies)
    client.cookies.clear()

    admin = login(client, admin_user.full_name)
    admin.post(f"/api/admin/users/{employee.id}/reset-password")
    client.cookies.clear()

    for name, value in victim_cookies.items():
        client.cookies.set(name, value)
    assert client.post("/api/auth/refresh").status_code == 401


def test_soft_delete_keeps_the_row_and_the_audit_trail(client, db, admin_user, employee, project):
    staff = login(client, employee.full_name)
    staff.post(f"/api/projects/{project.id}/open")
    staff.post("/api/auth/logout")

    admin = login(client, admin_user.full_name)
    assert admin.delete(f"/api/admin/users/{employee.id}").status_code == 200

    db.expire_all()
    stored = db.get(User, employee.id)
    assert stored is not None and stored.is_deleted is True

    # Deleted users disappear from the default list...
    listed = admin.get("/api/admin/users").json()
    assert employee.id not in [u["id"] for u in listed["items"]]
    # ...but their activity remains for the administrator.
    activity = admin.get(f"/api/admin/activity?employee_id={employee.employee_id}").json()
    assert activity["total"] > 0


def test_deleted_user_cannot_log_in(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    admin.delete(f"/api/admin/users/{employee.id}")
    admin.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": TEST_PASSWORD},
    ).status_code == 401


def test_admin_can_unlock_a_locked_account(client, db, admin_user, employee):
    from app.core.config import settings

    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS):
        client.post(
            "/api/auth/login",
            json={"username": employee.full_name, "password": "Wrong1!Password"},
        )
    admin = login(client, admin_user.full_name)
    assert admin.post(f"/api/admin/users/{employee.id}/unlock").status_code == 200
    admin.post("/api/auth/logout")

    assert client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": TEST_PASSWORD},
    ).status_code == 200


def test_user_list_never_exposes_password_hashes(as_admin, employee):
    response = as_admin.get("/api/admin/users")
    assert response.status_code == 200
    assert "password_hash" not in response.text
    assert "$argon2" not in response.text


def test_user_search_and_filters(as_admin, employee, other_employee):
    assert as_admin.get("/api/admin/users?search=Sofiyaan").json()["total"] == 1
    assert as_admin.get("/api/admin/users?search=ARWL12346").json()["total"] == 1
    assert as_admin.get("/api/admin/users?department=Portfolio").json()["total"] == 1
    assert as_admin.get("/api/admin/users?role=USER").json()["total"] == 2


def test_admin_can_view_a_users_activity_and_login_history(client, admin_user, employee):
    staff = login(client, employee.full_name)
    staff.post("/api/auth/logout")

    admin = login(client, admin_user.full_name)
    activity = admin.get(f"/api/admin/users/{employee.id}/activity").json()
    assert activity["total"] >= 1

    history = admin.get(f"/api/admin/users/{employee.id}/login-history").json()
    assert history["total"] >= 1
    assert history["items"][0]["successful"] is True


def test_profile_self_update_cannot_change_role(as_employee, db, employee):
    response = as_employee.put(
        "/api/auth/me", json={"full_name": "Sofiyaan S.", "role": "ADMIN"}
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Sofiyaan S."
    assert response.json()["role"] == "USER"

    db.expire_all()
    assert db.get(User, employee.id).role_name == "USER"


def test_employee_id_normalised_to_uppercase(as_admin):
    body = _create_employee(as_admin, employee_id="arwl99999", email="lower@example.com")
    assert body["user"]["employee_id"] == "ARWL99999"


def test_creating_a_user_needs_only_a_name_and_email(client, admin_user):
    """The admin supplies a name and an email; everything else is derived."""
    admin = login(client, admin_user.full_name)
    response = admin.post(
        "/api/admin/users",
        json={"full_name": "Ananya Krishnan", "email": "ananya.krishnan@example.com"},
    )
    assert response.status_code == 201, response.text
    body = response.json()

    # An internal identifier is allocated from the initials, not typed by hand.
    assert body["user"]["employee_id"] == "AK0001"
    assert body["user"]["role"] == "USER"
    assert body["temporary_password"]

    # And the new account signs in with the name that was entered.
    admin.post("/api/auth/logout")
    signed_in = client.post(
        "/api/auth/login",
        json={"username": "Ananya Krishnan", "password": body["temporary_password"]},
    )
    assert signed_in.status_code == 200


def test_generated_employee_ids_do_not_collide(client, admin_user):
    admin = login(client, admin_user.full_name)
    first = admin.post(
        "/api/admin/users",
        json={"full_name": "Ravi Kumar", "email": "ravi.kumar@example.com"},
    ).json()
    # Same initials, different person.
    second = admin.post(
        "/api/admin/users",
        json={"full_name": "Rohan Kapoor", "email": "rohan.kapoor@example.com"},
    ).json()

    assert first["user"]["employee_id"] == "RK0001"
    assert second["user"]["employee_id"] == "RK0002"


def test_an_explicit_employee_id_is_still_honoured(client, admin_user):
    admin = login(client, admin_user.full_name)
    body = admin.post(
        "/api/admin/users",
        json={
            "full_name": "Meera Iyer",
            "email": "meera.iyer@example.com",
            "employee_id": "ARWL55555",
        },
    ).json()
    assert body["user"]["employee_id"] == "ARWL55555"


def test_a_deleted_users_email_can_be_reused(client, admin_user):
    """Deleting is a soft delete; it must not reserve the address forever."""
    admin = login(client, admin_user.full_name)
    first = admin.post(
        "/api/admin/users",
        json={"full_name": "Temp Colleague", "email": "reuse.me@example.com"},
    )
    assert first.status_code == 201
    user_id = first.json()["user"]["id"]

    assert admin.delete(f"/api/admin/users/{user_id}").status_code == 200

    # Same address, and a different name so the name guard is not what passes it.
    again = admin.post(
        "/api/admin/users",
        json={"full_name": "Replacement Colleague", "email": "reuse.me@example.com"},
    )
    assert again.status_code == 201, again.text
    assert again.json()["user"]["id"] != user_id


def test_a_deleted_users_name_can_be_reused(client, admin_user):
    """A genuine re-hire signs in with the same name as before."""
    admin = login(client, admin_user.full_name)
    created = admin.post(
        "/api/admin/users",
        json={"full_name": "Returning Colleague", "email": "returning@example.com"},
    )
    assert created.status_code == 201
    admin.delete(f"/api/admin/users/{created.json()['user']['id']}")

    again = admin.post(
        "/api/admin/users",
        json={"full_name": "Returning Colleague", "email": "returning.2@example.com"},
    )
    assert again.status_code == 201, again.text


def test_two_live_users_still_cannot_share_an_email(client, admin_user):
    admin = login(client, admin_user.full_name)
    admin.post(
        "/api/admin/users", json={"full_name": "First Person", "email": "shared@example.com"}
    )
    clash = admin.post(
        "/api/admin/users", json={"full_name": "Second Person", "email": "shared@example.com"}
    )
    assert clash.status_code == 409


def test_employee_id_can_be_corrected_after_creation(client, admin_user):
    """IDs are generated now, so a placeholder or typo needs a way out."""
    admin = login(client, admin_user.full_name)
    created = _create_employee(admin, employee_id="ARWL00001")["user"]

    updated = admin.put(
        f"/api/admin/users/{created['id']}", json={"employee_id": "arwl-2024-7"}
    )
    assert updated.status_code == 200, updated.text
    # Normalised the same way creation does.
    assert updated.json()["employee_id"] == "ARWL-2024-7"


def test_changing_an_employee_id_does_not_end_the_session(client, admin_user):
    """The access token carries the ID but nothing reads it; sessions key on the user id."""
    admin = login(client, admin_user.full_name)
    before = admin.get("/api/auth/me").json()["employee_id"]

    changed = admin.put(
        f"/api/admin/users/{admin_user.id}", json={"employee_id": "NEWADMIN1"}
    )
    assert changed.status_code == 200

    me = admin.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["employee_id"] == "NEWADMIN1" != before


def test_employee_id_cannot_collide_with_a_live_account(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    response = admin.put(
        f"/api/admin/users/{employee.id}", json={"employee_id": admin_user.employee_id}
    )
    assert response.status_code == 409
    assert "already in use" in response.json()["message"]


def test_employee_id_may_reuse_one_freed_by_deletion(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    freed = _create_employee(admin, employee_id="FREEDID1")["user"]
    assert admin.delete(f"/api/admin/users/{freed['id']}").status_code == 200

    response = admin.put(f"/api/admin/users/{employee.id}", json={"employee_id": "FREEDID1"})
    assert response.status_code == 200
    assert response.json()["employee_id"] == "FREEDID1"


def test_an_invalid_employee_id_is_rejected(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    assert admin.put(
        f"/api/admin/users/{employee.id}", json={"employee_id": "has spaces!"}
    ).status_code == 422


def test_the_employee_id_change_is_audited(client, admin_user, employee, db):
    from app.models.activity import ActivityLog

    admin = login(client, admin_user.full_name)
    old_id = employee.employee_id
    admin.put(f"/api/admin/users/{employee.id}", json={"employee_id": "AUDITED1"})

    log = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == "USER_UPDATED")
        .order_by(ActivityLog.id.desc())
    ).scalars().first()
    assert log is not None
    assert f"{old_id} -> AUDITED1" in str(log.event_metadata)
