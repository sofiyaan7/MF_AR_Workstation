"""Authentication, lockout, sessions and password management."""
import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.enums import AccountStatus, EventType, RoleName
from app.models.activity import ActivityLog
from app.models.user import LoginAttempt, Session, User
from tests.conftest import TEST_PASSWORD, login


def test_login_success_sets_cookies_and_profile(client, employee):
    response = client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": TEST_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["employee_id"] == "ARWL12345"
    assert body["user"]["full_name"] == "Sofiyaan Sameer"
    assert body["user"]["role"] == "USER"
    assert body["csrf_token"]
    assert settings.ACCESS_COOKIE_NAME in response.cookies
    assert settings.REFRESH_COOKIE_NAME in response.cookies


def test_login_response_never_exposes_password_hash(client, employee):
    response = client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": TEST_PASSWORD},
    )
    assert "password_hash" not in response.text
    assert "$argon2" not in response.text


def test_login_wrong_password_rejected(client, employee):
    response = client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": "WrongPassword1!"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid Employee ID or password"


def test_login_unknown_employee_id_gives_identical_error(client, employee):
    response = client.post(
        "/api/auth/login",
        json={"username": "NOT-A-REAL-ID", "password": TEST_PASSWORD},
    )
    assert response.status_code == 401
    # Identical wording prevents employee-ID enumeration.
    assert response.json()["message"] == "Invalid Employee ID or password"


def test_only_authorized_employees_can_log_in(client, db, roles):
    """An Employee ID that an administrator never added cannot sign in."""
    response = client.post(
        "/api/auth/login", json={"username": "ARWL99999", "password": TEST_PASSWORD}
    )
    assert response.status_code == 401
    assert db.execute(
        select(User).where(User.employee_id == "ARWL99999")
    ).scalars().first() is None


def test_disabled_user_cannot_log_in(client, db, roles):
    from tests.conftest import _make_user

    user = _make_user(
        db, roles, "ARWL55555", "Disabled Person", "USER",
        status=AccountStatus.DISABLED, is_active=False,
    )
    response = client.post(
        "/api/auth/login", json={"username": user.full_name, "password": TEST_PASSWORD}
    )
    assert response.status_code == 401
    assert "not active" in response.json()["message"]


def test_account_locks_after_repeated_failures(client, db, employee):
    for _ in range(settings.MAX_FAILED_LOGIN_ATTEMPTS - 1):
        client.post(
            "/api/auth/login",
            json={"username": employee.full_name, "password": "Wrong1!Password"},
        )
    final = client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": "Wrong1!Password"},
    )
    assert final.status_code == 423
    assert "locked" in final.json()["message"].lower()

    # Even the correct password is refused while locked.
    correct = client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": TEST_PASSWORD},
    )
    assert correct.status_code == 423

    db.expire_all()
    refreshed = db.get(User, employee.id)
    assert refreshed.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS
    assert refreshed.locked_until is not None


def test_failed_logins_are_recorded(client, db, employee):
    client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": "Wrong1!Password"},
    )
    attempts = db.execute(select(LoginAttempt)).scalars().all()
    assert len(attempts) == 1
    assert attempts[0].successful is False
    assert attempts[0].failure_reason == "bad_password"

    logs = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.FAILED_LOGIN)
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].success is False


def test_successful_login_is_audited_and_counted(client, db, employee):
    login(client, employee.full_name)
    db.expire_all()
    refreshed = db.get(User, employee.id)
    assert refreshed.login_count == 1
    assert refreshed.last_login_at is not None

    logs = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.LOGIN)
    ).scalars().all()
    assert len(logs) == 1
    assert logs[0].employee_id == employee.employee_id


def test_me_requires_authentication(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_signed_in_user(as_employee, employee):
    response = as_employee.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["employee_id"] == employee.employee_id


def test_logout_revokes_the_session(client, db, employee):
    api = login(client, employee.full_name)
    assert api.post("/api/auth/logout").status_code == 200

    sessions = db.execute(select(Session)).scalars().all()
    assert all(s.revoked_at is not None for s in sessions)
    assert client.get("/api/auth/me").status_code == 401


def test_refresh_rotates_the_token(client, db, employee):
    login(client, employee.full_name)
    first_refresh = client.cookies.get(settings.REFRESH_COOKIE_NAME)

    response = client.post("/api/auth/refresh")
    assert response.status_code == 200
    assert client.cookies.get(settings.REFRESH_COOKIE_NAME) != first_refresh

    sessions = db.execute(select(Session).order_by(Session.id)).scalars().all()
    assert len(sessions) == 2
    assert sessions[0].revoked_at is not None   # old one revoked
    assert sessions[1].revoked_at is None       # new one live


def test_revoked_refresh_token_cannot_be_reused(client, employee):
    """Rotation means a captured refresh token is dead after the next refresh."""
    login(client, employee.full_name)
    stolen = client.cookies.get(settings.REFRESH_COOKIE_NAME)
    client.post("/api/auth/refresh")

    # Present the old token on its own; the cookie jar is cleared first so the
    # rotated token cannot be sent alongside it.
    client.cookies.clear()
    client.cookies.set(settings.REFRESH_COOKIE_NAME, stolen)
    assert client.post("/api/auth/refresh").status_code == 401


def test_garbage_refresh_token_rejected(client):
    client.cookies.set(settings.REFRESH_COOKIE_NAME, "not-a-real-token")
    assert client.post("/api/auth/refresh").status_code == 401


def test_access_token_forged_with_another_key_is_rejected(client, employee):
    """A token signed with a different secret must not authenticate."""
    from jose import jwt

    forged = jwt.encode(
        {"sub": str(employee.id), "type": "access", "exp": 9999999999},
        "an-attacker-chosen-secret",
        algorithm="HS256",
    )
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_change_password_succeeds_and_new_password_works(client, employee):
    api = login(client, employee.full_name)
    new_password = "Br@ndNewPass99"
    response = api.post(
        "/api/auth/change-password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": new_password,
            "confirm_password": new_password,
        },
    )
    assert response.status_code == 200

    api.post("/api/auth/logout")
    assert client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": new_password},
    ).status_code == 200
    assert client.post(
        "/api/auth/login",
        json={"username": employee.full_name, "password": TEST_PASSWORD},
    ).status_code == 401


def test_change_password_rejects_wrong_current_password(as_employee):
    response = as_employee.post(
        "/api/auth/change-password",
        json={
            "current_password": "NotMyPassword1!",
            "new_password": "Br@ndNewPass99",
            "confirm_password": "Br@ndNewPass99",
        },
    )
    assert response.status_code == 401
    assert "current password is incorrect" in response.json()["message"]


def test_change_password_rejects_mismatched_confirmation(as_employee):
    response = as_employee.post(
        "/api/auth/change-password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "Br@ndNewPass99",
            "confirm_password": "Different1!Pass",
        },
    )
    assert response.status_code == 422


@pytest.mark.parametrize(
    "weak",
    ["short1!A", "alllowercase123!", "ALLUPPERCASE123!", "NoNumbers!Here", "NoSpecial123ABC"],
)
def test_change_password_enforces_complexity(as_employee, weak):
    response = as_employee.post(
        "/api/auth/change-password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": weak,
            "confirm_password": weak,
        },
    )
    assert response.status_code == 422
    assert response.json()["details"]


def test_change_password_blocks_reuse(as_employee):
    response = as_employee.post(
        "/api/auth/change-password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 422
    message = response.json()["message"].lower()
    assert "reuse" in message or "different" in message


def test_password_change_is_audited(client, db, employee):
    api = login(client, employee.full_name)
    api.post(
        "/api/auth/change-password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "Br@ndNewPass99",
            "confirm_password": "Br@ndNewPass99",
        },
    )
    logs = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.PASSWORD_CHANGED)
    ).scalars().all()
    assert len(logs) == 1 and logs[0].success is True


def test_forgot_password_does_not_reveal_whether_the_name_exists(client, employee):
    known = client.post(
        "/api/auth/forgot-password", json={"username": employee.full_name}
    )
    unknown = client.post("/api/auth/forgot-password", json={"username": "Nobody At All"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()


def test_password_policy_endpoint_is_public(client):
    response = client.get("/api/auth/password-policy")
    assert response.status_code == 200
    assert response.json()["min_length"] == settings.PASSWORD_MIN_LENGTH


def test_csrf_token_required_for_cookie_state_changes(client, employee):
    login(client, employee.full_name)  # cookies set, but no CSRF header sent below
    response = client.post(
        "/api/auth/change-password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": "Br@ndNewPass99",
            "confirm_password": "Br@ndNewPass99",
        },
    )
    assert response.status_code == 403
    assert "CSRF" in response.json()["message"]


def test_security_headers_present(client):
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers


def test_sign_in_uses_the_full_name_not_the_employee_id(client, employee):
    """The username is the person's name; the employee ID is no longer a credential."""
    by_name = client.post(
        "/api/auth/login", json={"username": employee.full_name, "password": TEST_PASSWORD}
    )
    assert by_name.status_code == 200

    by_id = client.post(
        "/api/auth/login", json={"username": employee.employee_id, "password": TEST_PASSWORD}
    )
    assert by_id.status_code == 401


def test_name_matching_ignores_case_and_extra_spacing(client, employee):
    response = client.post(
        "/api/auth/login",
        json={"username": f"  {employee.full_name.upper()}  ", "password": TEST_PASSWORD},
    )
    assert response.status_code == 200


def test_a_deleted_namesake_does_not_block_sign_in(client, db, roles, employee):
    """One live account and one deleted namesake still resolves to the live one."""
    from tests.conftest import _make_user

    ghost = _make_user(db, roles, "ARWL90001", employee.full_name, RoleName.USER)
    ghost.is_deleted = True
    db.commit()

    response = client.post(
        "/api/auth/login", json={"username": employee.full_name, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200


def test_two_sign_in_able_namesakes_are_refused_rather_than_guessed(client, db, roles, employee):
    """Signing one of two namesakes in would be signing them into the wrong account."""
    from tests.conftest import _make_user

    _make_user(db, roles, "ARWL90002", employee.full_name, RoleName.USER)
    db.commit()

    response = client.post(
        "/api/auth/login", json={"username": employee.full_name, "password": TEST_PASSWORD}
    )
    assert response.status_code == 401
    # The generic message must not hint that the name matched several accounts.
    assert "Invalid" in response.json()["message"]


def test_duplicate_sign_in_names_are_rejected_at_creation(client, admin_user, employee):
    from tests.conftest import login as sign_in

    admin = sign_in(client, admin_user.full_name)
    response = admin.post(
        "/api/admin/users",
        json={
            "employee_id": "ARWL90003",
            "full_name": employee.full_name.lower(),
            "email": "namesake@example.com",
            "role": "USER",
            "status": "ACTIVE",
        },
    )
    assert response.status_code == 409
    assert "sign-in name" in response.json()["message"]
