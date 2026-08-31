"""Category management."""
from tests.conftest import login


def test_admin_crud_for_categories(as_admin):
    created = as_admin.post(
        "/api/admin/categories",
        json={"name": "Index Research", "description": "Index reviews", "icon": "Microscope"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["slug"] == "index-research"

    updated = as_admin.put(
        f"/api/admin/categories/{body['id']}", json={"name": "Index & Benchmarks"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Index & Benchmarks"
    assert updated.json()["slug"] == "index-benchmarks"

    assert as_admin.delete(f"/api/admin/categories/{body['id']}").status_code == 200
    assert as_admin.get("/api/admin/categories").json() == []


def test_duplicate_category_name_rejected(as_admin, category):
    response = as_admin.post("/api/admin/categories", json={"name": "Research"})
    assert response.status_code == 409


def test_category_in_use_cannot_be_deleted(as_admin, category, project):
    response = as_admin.delete(f"/api/admin/categories/{category.id}")
    assert response.status_code == 409
    assert "1 project" in response.json()["message"]


def test_employees_can_read_categories_with_counts(as_employee, category, project):
    body = as_employee.get("/api/projects/categories").json()
    assert len(body) == 1
    assert body[0]["name"] == "Research"
    assert body[0]["project_count"] == 1


def test_employee_cannot_create_a_category(as_employee):
    assert as_employee.post(
        "/api/admin/categories", json={"name": "Sneaky"}
    ).status_code == 403


def test_category_counts_exclude_hidden_projects(client, admin_user, employee, category):
    admin = login(client, admin_user.employee_id)
    admin.post(
        "/api/admin/projects",
        json={
            "name": "Admin Console",
            "url": "https://example.internal/console",
            "category_id": category.id,
            "visibility": "ADMIN_ONLY",
        },
    )
    admin.post("/api/auth/logout")

    staff = login(client, employee.employee_id)
    assert staff.get("/api/projects").json()["total"] == 0
