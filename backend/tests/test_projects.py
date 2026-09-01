"""Project catalogue: CRUD, visibility, favourites, opens and search."""
from sqlalchemy import select

from app.models.activity import ActivityLog
from app.models.enums import EventType
from app.models.project import Favourite, Project, ProjectOpen
from tests.conftest import login


def _create_project(api, **overrides) -> dict:
    payload = {
        "name": "MSCI August Review",
        "url": "https://example.internal/msci-august",
        "description": "MSCI August 2026 index review analysis and backtesting dashboard.",
        "category_id": None,
        "tags": ["MSCI", "Research", "Backtesting"],
        "owner_name": "Sofiyaan",
        "status": "ACTIVE",
        "visibility": "ALL_EMPLOYEES",
        "is_featured": True,
    }
    payload.update(overrides)
    response = api.post("/api/admin/projects", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------
# Creation appears on the dashboard with no code change
# --------------------------------------------------------------------------
def test_admin_creates_project_and_it_appears_for_employees(client, admin_user, employee, category):
    admin = login(client, admin_user.full_name)
    created = _create_project(admin, category_id=category.id)
    assert created["name"] == "MSCI August Review"
    assert created["slug"] == "msci-august-review"
    assert {t["name"] for t in created["tags"]} == {"MSCI", "Research", "Backtesting"}
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    listed = staff.get("/api/projects").json()
    assert created["id"] in [p["id"] for p in listed["items"]]

    dashboard = staff.get("/api/projects/dashboard").json()
    assert created["id"] in [p["id"] for p in dashboard["featured"]]


def test_created_project_records_who_created_it(client, admin_user, category):
    admin = login(client, admin_user.full_name)
    created = _create_project(admin, category_id=category.id)
    assert created["created_by_id"] == admin_user.id

    detail = admin.get(f"/api/admin/projects/{created['id']}").json()
    assert detail["created_by_id"] == admin_user.id


def test_project_creation_is_audited(client, db, admin_user, category):
    admin = login(client, admin_user.full_name)
    created = _create_project(admin, category_id=category.id)
    log = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.PROJECT_CREATED)
    ).scalars().one()
    assert log.project_id == created["id"]
    assert log.user_id == admin_user.id


def test_project_url_must_be_http_or_https(as_admin):
    response = as_admin.post(
        "/api/admin/projects",
        json={"name": "Evil", "url": "javascript:alert(document.cookie)"},
    )
    assert response.status_code == 422


def test_project_requires_a_url(as_admin):
    assert as_admin.post("/api/admin/projects", json={"name": "No URL"}).status_code == 422


# --------------------------------------------------------------------------
# Update / delete
# --------------------------------------------------------------------------
def test_admin_can_edit_a_project(as_admin, project):
    response = as_admin.put(
        f"/api/admin/projects/{project.id}",
        json={"name": "MSCI Review (2026)", "status": "MAINTENANCE"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "MSCI Review (2026)"
    assert body["status"] == "MAINTENANCE"


def test_edit_is_audited_with_the_editor(as_admin, db, project, admin_user):
    as_admin.put(f"/api/admin/projects/{project.id}", json={"name": "Renamed"})
    log = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.PROJECT_UPDATED)
    ).scalars().one()
    assert log.user_id == admin_user.id


def test_delete_is_soft_and_hides_the_project(client, db, admin_user, employee, project):
    admin = login(client, admin_user.full_name)
    assert admin.delete(f"/api/admin/projects/{project.id}").status_code == 200
    admin.post("/api/auth/logout")

    db.expire_all()
    stored = db.get(Project, project.id)
    assert stored is not None and stored.is_deleted is True

    staff = login(client, employee.full_name)
    assert staff.get("/api/projects").json()["items"] == []
    assert staff.get(f"/api/projects/{project.id}").status_code == 404


def test_activity_history_survives_project_deletion(client, db, admin_user, employee, project):
    staff = login(client, employee.full_name)
    staff.post(f"/api/projects/{project.id}/open")
    staff.post("/api/auth/logout")

    admin = login(client, admin_user.full_name)
    admin.delete(f"/api/admin/projects/{project.id}")

    activity = admin.get("/api/admin/activity?event_type=PROJECT_OPENED").json()
    assert activity["total"] == 1
    assert activity["items"][0]["project_name"] == "MSCI Review Dashboard"
    assert activity["items"][0]["employee_id"] == employee.employee_id


def test_deleted_project_can_be_restored(as_admin, project):
    as_admin.delete(f"/api/admin/projects/{project.id}")
    restored = as_admin.post(f"/api/admin/projects/{project.id}/restore")
    assert restored.status_code == 200
    assert restored.json()["is_active"] is True


def test_duplicate_creates_an_inactive_copy(as_admin, project):
    response = as_admin.post(f"/api/admin/projects/{project.id}/duplicate")
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "MSCI Review Dashboard (Copy)"
    assert body["is_active"] is False
    assert body["id"] != project.id


# --------------------------------------------------------------------------
# Visibility — enforced by the backend, not by hiding in the UI
# --------------------------------------------------------------------------
def test_admin_only_project_is_invisible_to_employees(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    created = _create_project(
        admin, name="Risk Limits Console", visibility="ADMIN_ONLY",
        url="https://example.internal/risk",
    )
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    assert created["id"] not in [p["id"] for p in staff.get("/api/projects").json()["items"]]
    # Direct fetch is refused too, and does not confirm the project exists.
    assert staff.get(f"/api/projects/{created['id']}").status_code == 404
    assert staff.post(f"/api/projects/{created['id']}/open").status_code == 404


def test_specific_employees_visibility_grants_only_named_ids(
    client, admin_user, employee, other_employee
):
    admin = login(client, admin_user.full_name)
    created = _create_project(
        admin,
        name="Sector Rotation Model",
        url="https://example.internal/sector",
        visibility="SPECIFIC_EMPLOYEES",
        allowed_employee_ids=[employee.employee_id],
    )
    admin.post("/api/auth/logout")

    permitted = login(client, employee.full_name)
    assert created["id"] in [p["id"] for p in permitted.get("/api/projects").json()["items"]]
    assert permitted.get(f"/api/projects/{created['id']}").status_code == 200
    permitted.post("/api/auth/logout")

    excluded = login(client, other_employee.full_name)
    assert created["id"] not in [p["id"] for p in excluded.get("/api/projects").json()["items"]]
    assert excluded.get(f"/api/projects/{created['id']}").status_code == 404


def test_department_restriction_is_enforced(client, admin_user, employee, other_employee):
    """employee is in Research; other_employee is in Portfolio."""
    admin = login(client, admin_user.full_name)
    created = _create_project(
        admin, name="Research Only Tool", url="https://example.internal/research-only",
        allowed_departments=["Research"],
    )
    admin.post("/api/auth/logout")

    in_dept = login(client, employee.full_name)
    assert in_dept.get(f"/api/projects/{created['id']}").status_code == 200
    in_dept.post("/api/auth/logout")

    out_of_dept = login(client, other_employee.full_name)
    assert out_of_dept.get(f"/api/projects/{created['id']}").status_code == 404


def test_visibility_change_takes_effect_immediately(client, admin_user, employee, project):
    staff = login(client, employee.full_name)
    assert staff.get(f"/api/projects/{project.id}").status_code == 200
    staff.post("/api/auth/logout")

    admin = login(client, admin_user.full_name)
    admin.put(f"/api/admin/projects/{project.id}", json={"visibility": "ADMIN_ONLY"})
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    assert staff.get(f"/api/projects/{project.id}").status_code == 404


def test_inactive_project_is_hidden_from_employees(client, admin_user, employee, project):
    admin = login(client, admin_user.full_name)
    admin.put(f"/api/admin/projects/{project.id}", json={"is_active": False})
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    assert staff.get("/api/projects").json()["items"] == []


# --------------------------------------------------------------------------
# Opening
# --------------------------------------------------------------------------
def test_open_returns_the_url_and_records_usage(as_employee, db, employee, project):
    response = as_employee.post(f"/api/projects/{project.id}/open")
    assert response.status_code == 200
    body = response.json()
    assert body["url"] == "https://example.internal/msci"
    assert body["open_in_new_tab"] is True

    db.expire_all()
    assert db.get(Project, project.id).total_opens == 1
    opens = db.execute(select(ProjectOpen)).scalars().all()
    assert len(opens) == 1 and opens[0].user_id == employee.id

    log = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.PROJECT_OPENED)
    ).scalars().one()
    assert log.project_id == project.id
    assert log.employee_id == employee.employee_id
    assert log.ip_address is not None


def test_open_appears_in_recently_used(as_employee, project):
    as_employee.post(f"/api/projects/{project.id}/open")
    recent = as_employee.get("/api/projects/recent").json()
    assert len(recent) == 1
    assert recent[0]["project"]["id"] == project.id
    assert recent[0]["last_opened_at"]


def test_recently_used_is_per_user(client, employee, other_employee, project):
    mine = login(client, employee.full_name)
    mine.post(f"/api/projects/{project.id}/open")
    mine.post("/api/auth/logout")

    theirs = login(client, other_employee.full_name)
    assert theirs.get("/api/projects/recent").json() == []


def test_coming_soon_project_cannot_be_opened(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    created = _create_project(
        admin, name="Future Tool", url="https://example.internal/future", status="COMING_SOON"
    )
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    response = staff.post(f"/api/projects/{created['id']}/open")
    assert response.status_code == 403


# --------------------------------------------------------------------------
# Favourites
# --------------------------------------------------------------------------
def test_favourite_and_unfavourite(as_employee, db, employee, project):
    assert as_employee.post(f"/api/projects/{project.id}/favourite").status_code == 200
    assert db.execute(select(Favourite)).scalars().all()

    favourites = as_employee.get("/api/projects/favourites").json()
    assert [p["id"] for p in favourites] == [project.id]
    assert favourites[0]["is_favourite"] is True

    assert as_employee.delete(f"/api/projects/{project.id}/favourite").status_code == 200
    assert as_employee.get("/api/projects/favourites").json() == []


def test_favourites_are_per_user(client, employee, other_employee, project):
    mine = login(client, employee.full_name)
    mine.post(f"/api/projects/{project.id}/favourite")
    mine.post("/api/auth/logout")

    theirs = login(client, other_employee.full_name)
    assert theirs.get("/api/projects/favourites").json() == []
    assert theirs.get("/api/projects").json()["items"][0]["is_favourite"] is False


def test_duplicate_favourite_is_rejected(as_employee, project):
    as_employee.post(f"/api/projects/{project.id}/favourite")
    assert as_employee.post(f"/api/projects/{project.id}/favourite").status_code == 409


def test_favouriting_is_audited(as_employee, db, project):
    as_employee.post(f"/api/projects/{project.id}/favourite")
    as_employee.delete(f"/api/projects/{project.id}/favourite")
    events = [
        log.event_type
        for log in db.execute(
            select(ActivityLog).order_by(ActivityLog.id)
        ).scalars().all()
    ]
    assert EventType.PROJECT_FAVOURITED in events
    assert EventType.PROJECT_UNFAVOURITED in events


def test_cannot_favourite_a_project_you_cannot_see(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    created = _create_project(
        admin, name="Hidden", url="https://example.internal/hidden", visibility="ADMIN_ONLY"
    )
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    assert staff.post(f"/api/projects/{created['id']}/favourite").status_code == 404


# --------------------------------------------------------------------------
# Search / filter / sort
# --------------------------------------------------------------------------
def test_search_matches_name_description_tag_and_owner(client, admin_user, employee, category):
    admin = login(client, admin_user.full_name)
    _create_project(admin, name="MSCI August Review", category_id=category.id)
    _create_project(
        admin, name="Portfolio Audit", url="https://example.internal/audit",
        description="Client portfolio analysis tool", tags=["Audit"],
        owner_name="Rahul", category_id=category.id,
    )
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    assert staff.get("/api/projects?search=MSCI").json()["total"] == 1
    assert staff.get("/api/projects?search=portfolio").json()["total"] == 1
    assert staff.get("/api/projects?search=Backtesting").json()["total"] == 1  # tag
    assert staff.get("/api/projects?search=Rahul").json()["total"] == 1        # owner
    assert staff.get("/api/projects?search=zzzz").json()["total"] == 0


def test_search_is_case_insensitive(as_employee, project):
    assert as_employee.get("/api/projects?search=msci").json()["total"] == 1
    assert as_employee.get("/api/projects?search=MSCI").json()["total"] == 1


def test_filter_by_category_and_status(client, admin_user, employee, category):
    admin = login(client, admin_user.full_name)
    _create_project(admin, category_id=category.id)
    _create_project(
        admin, name="Deprecated Tool", url="https://example.internal/old",
        status="DEPRECATED", category_id=None,
    )
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    assert staff.get(f"/api/projects?category_id={category.id}").json()["total"] == 1
    assert staff.get("/api/projects?status=DEPRECATED").json()["total"] == 1


def test_sort_by_name_and_most_used(client, admin_user, employee, category):
    admin = login(client, admin_user.full_name)
    first = _create_project(admin, name="Alpha Tool", category_id=category.id)
    _create_project(admin, name="Beta Tool", url="https://example.internal/beta",
                    category_id=category.id)
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    names = [p["name"] for p in staff.get("/api/projects?sort=name").json()["items"]]
    assert names == ["Alpha Tool", "Beta Tool"]

    staff.post(f"/api/projects/{first['id']}/open")
    top = staff.get("/api/projects?sort=most_used").json()["items"][0]
    assert top["name"] == "Alpha Tool"


def test_search_only_covers_visible_projects(client, admin_user, employee):
    admin = login(client, admin_user.full_name)
    _create_project(
        admin, name="Secret MSCI Console", url="https://example.internal/secret",
        visibility="ADMIN_ONLY",
    )
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    assert staff.get("/api/projects?search=MSCI").json()["total"] == 0


def test_project_detail_view_is_audited(as_employee, db, project):
    as_employee.get(f"/api/projects/{project.id}")
    log = db.execute(
        select(ActivityLog).where(ActivityLog.event_type == EventType.PROJECT_VIEWED)
    ).scalars().one()
    assert log.project_id == project.id


def test_project_detail_hides_permission_list_from_employees(
    client, admin_user, employee, other_employee
):
    admin = login(client, admin_user.full_name)
    created = _create_project(
        admin, name="Pilot Tool", url="https://example.internal/pilot",
        visibility="SPECIFIC_EMPLOYEES",
        allowed_employee_ids=[employee.employee_id, other_employee.employee_id],
    )
    admin.post("/api/auth/logout")

    staff = login(client, employee.full_name)
    detail = staff.get(f"/api/projects/{created['id']}").json()
    # A permitted employee must not learn who else has access.
    assert detail["allowed_employee_ids"] == []
    assert other_employee.employee_id not in staff.get(
        f"/api/projects/{created['id']}"
    ).text
