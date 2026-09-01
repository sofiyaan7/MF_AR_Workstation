"""Per-project change suggestions: the shared open/closed log."""
from tests.conftest import login


def _create(api, project_id, title="Add a CSV export", body="The review team needs raw rows."):
    return api.post(
        f"/api/projects/{project_id}/suggestions", json={"title": title, "body": body}
    )


def test_employee_can_raise_a_suggestion(as_employee, project):
    response = _create(as_employee, project.id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "OPEN"
    assert body["title"] == "Add a CSV export"
    assert body["closed_at"] is None
    assert body["user"]["employee_id"]


def test_the_log_is_shared_between_users(as_employee, client, other_employee, project):
    _create(as_employee, project.id, title="Raised by the first employee")

    # A different employee sees it: the log is deliberately not private.
    as_other = login(client, other_employee.employee_id)
    listing = as_other.get(f"/api/projects/{project.id}/suggestions")
    assert listing.status_code == 200
    titles = [item["title"] for item in listing.json()["items"]]
    assert "Raised by the first employee" in titles


def test_counts_cover_open_and_closed(as_employee, as_admin, project):
    first = _create(as_employee, project.id, title="Stays open").json()
    second = _create(as_employee, project.id, title="Gets closed").json()

    closed = as_admin.patch(
        f"/api/projects/{project.id}/suggestions/{second['id']}", json={"status": "CLOSED"}
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "CLOSED"
    assert closed.json()["closed_at"] is not None

    listing = as_employee.get(f"/api/projects/{project.id}/suggestions").json()
    assert listing["counts"] == {"open": 1, "closed": 1, "total": 2}
    assert {i["id"] for i in listing["items"]} == {first["id"], second["id"]}


def test_status_filter_does_not_change_the_counts(as_employee, as_admin, project):
    _create(as_employee, project.id, title="Open one")
    second = _create(as_employee, project.id, title="Closed one").json()
    as_admin.patch(
        f"/api/projects/{project.id}/suggestions/{second['id']}", json={"status": "CLOSED"}
    )

    filtered = as_employee.get(
        f"/api/projects/{project.id}/suggestions", params={"status": "OPEN"}
    ).json()
    assert [i["title"] for i in filtered["items"]] == ["Open one"]
    # Tab labels must keep showing project-wide totals while a filter is applied.
    assert filtered["counts"] == {"open": 1, "closed": 1, "total": 2}


def test_author_can_close_and_reopen_their_own(as_employee, project):
    created = _create(as_employee, project.id).json()
    assert created["can_manage"] is True

    closed = as_employee.patch(
        f"/api/projects/{project.id}/suggestions/{created['id']}", json={"status": "CLOSED"}
    )
    assert closed.status_code == 200
    assert closed.json()["closed_by"]["employee_id"]

    reopened = as_employee.patch(
        f"/api/projects/{project.id}/suggestions/{created['id']}", json={"status": "OPEN"}
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "OPEN"
    assert reopened.json()["closed_at"] is None
    assert reopened.json()["closed_by"] is None


def test_another_employee_cannot_close_someone_elses(
    as_employee, client, other_employee, project
):
    created = _create(as_employee, project.id).json()
    as_other = login(client, other_employee.employee_id)

    listing = as_other.get(f"/api/projects/{project.id}/suggestions").json()
    assert listing["items"][0]["can_manage"] is False

    response = as_other.patch(
        f"/api/projects/{project.id}/suggestions/{created['id']}", json={"status": "CLOSED"}
    )
    assert response.status_code == 403


def test_admin_can_close_anyones(as_employee, as_admin, project):
    created = _create(as_employee, project.id).json()
    response = as_admin.patch(
        f"/api/projects/{project.id}/suggestions/{created['id']}", json={"status": "CLOSED"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "CLOSED"


def test_title_is_validated(as_employee, project):
    assert _create(as_employee, project.id, title="ab").status_code == 422


def test_suggestion_from_another_project_is_not_reachable(as_employee, as_admin, project, db):
    from app.models.project import Project

    other = Project(
        name="Unrelated", slug="unrelated", url="https://example.internal/other",
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    created = _create(as_employee, project.id).json()
    # Correct id, wrong project in the path: must not resolve.
    response = as_employee.get(f"/api/projects/{other.id}/suggestions")
    assert response.status_code == 200
    assert response.json()["items"] == []

    mismatched = as_employee.patch(
        f"/api/projects/{other.id}/suggestions/{created['id']}", json={"status": "CLOSED"}
    )
    assert mismatched.status_code == 404
