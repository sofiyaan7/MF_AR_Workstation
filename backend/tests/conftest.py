"""Test fixtures.

The suite runs against a throwaway SQLite database. The environment must be
configured *before* the application modules are imported, because the engine is
created at import time.
"""
import os
import tempfile

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-used-in-production-0123456789")
os.environ.setdefault("PASSWORD_MIN_LENGTH", "12")
os.environ.setdefault("MAX_FAILED_LOGIN_ATTEMPTS", "5")
os.environ.setdefault("LOGIN_RATE_LIMIT_ATTEMPTS", "50")
_DB_FD, _DB_PATH = tempfile.mkstemp(suffix=".db", prefix="mfar_test_")
os.close(_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_DB_PATH}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app.core import security  # noqa: E402
from app.database.base import Base, utcnow  # noqa: E402
from app.database.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import AccountStatus, RoleName  # noqa: E402
from app.models.project import Category, Project  # noqa: E402
from app.models.user import PasswordHistory, Role, User  # noqa: E402

TEST_PASSWORD = "Str0ng!Passw0rd42"


@event.listens_for(engine, "connect")
def _enable_sqlite_fks(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    try:
        os.unlink(_DB_PATH)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _clean_tables(_schema):
    """Truncate between tests so each one starts from a known state."""
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.exec_driver_sql(f'DELETE FROM "{table.name}"')


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    finally:
        session.close()


@pytest.fixture
def roles(db) -> dict[str, Role]:
    from app.database.seed import seed_roles

    result = seed_roles(db)
    db.commit()
    return result


def _make_user(
    db, roles, employee_id: str, name: str, role: str, *,
    password: str = TEST_PASSWORD, department: str | None = "Research",
    status: str = AccountStatus.ACTIVE, is_active: bool = True,
    must_change_password: bool = False,
) -> User:
    user = User(
        employee_id=employee_id,
        full_name=name,
        email=f"{employee_id.lower()}@example.com",
        department=department,
        role_id=roles[str(role)].id,
        password_hash=security.hash_password(password),
        password_changed_at=utcnow(),
        status=str(status),
        is_active=is_active,
        must_change_password=must_change_password,
    )
    db.add(user)
    db.commit()
    db.add(PasswordHistory(
        user_id=user.id, password_hash=user.password_hash, created_at=utcnow()
    ))
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_user(db, roles) -> User:
    return _make_user(db, roles, "ADMIN001", "System Administrator", RoleName.SUPER_ADMIN,
                      department="Administration")


@pytest.fixture
def plain_admin(db, roles) -> User:
    return _make_user(db, roles, "ADMIN002", "Department Admin", RoleName.ADMIN)


@pytest.fixture
def employee(db, roles) -> User:
    return _make_user(db, roles, "ARWL12345", "Sofiyaan Sameer", RoleName.USER)


@pytest.fixture
def other_employee(db, roles) -> User:
    return _make_user(db, roles, "ARWL12346", "Rahul Mehta", RoleName.USER,
                      department="Portfolio")


@pytest.fixture
def category(db) -> Category:
    cat = Category(name="Research", slug="research", sort_order=10)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@pytest.fixture
def project(db, category, admin_user) -> Project:
    proj = Project(
        name="MSCI Review Dashboard",
        slug="msci-review-dashboard",
        url="https://example.internal/msci",
        short_description="Index review analysis",
        category_id=category.id,
        owner_name="Sofiyaan Sameer",
        created_by_id=admin_user.id,
        is_featured=True,
    )
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


class ApiClient:
    """Thin wrapper that carries the CSRF header for a signed-in session."""

    def __init__(self, client: TestClient, csrf: str | None = None):
        self.client = client
        self.csrf = csrf

    def _headers(self, extra: dict | None = None) -> dict:
        headers = dict(extra or {})
        if self.csrf:
            headers.setdefault("X-CSRF-Token", self.csrf)
        return headers

    def get(self, url, **kw):
        return self.client.get(url, headers=self._headers(kw.pop("headers", None)), **kw)

    def post(self, url, **kw):
        return self.client.post(url, headers=self._headers(kw.pop("headers", None)), **kw)

    def put(self, url, **kw):
        return self.client.put(url, headers=self._headers(kw.pop("headers", None)), **kw)

    def patch(self, url, **kw):
        return self.client.patch(url, headers=self._headers(kw.pop("headers", None)), **kw)

    def delete(self, url, **kw):
        return self.client.delete(url, headers=self._headers(kw.pop("headers", None)), **kw)


def login(client: TestClient, employee_id: str, password: str = TEST_PASSWORD) -> ApiClient:
    response = client.post(
        "/api/auth/login", json={"employee_id": employee_id, "password": password}
    )
    assert response.status_code == 200, response.text
    return ApiClient(client, response.json()["csrf_token"])


@pytest.fixture
def as_admin(client, admin_user) -> ApiClient:
    return login(client, admin_user.employee_id)


@pytest.fixture
def as_employee(client, employee) -> ApiClient:
    return login(client, employee.employee_id)
