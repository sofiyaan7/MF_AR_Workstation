"""Administrator project and category management."""
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.auth.dependencies import AdminUser, Ctx, Db
from app.core.exceptions import ConflictError, NotFoundError, ValidationError
from app.database.base import utcnow
from app.models.enums import EventType, Visibility
from app.models.project import Category, Project, ProjectOpen
from app.schemas.activity import ProjectStatsResponse
from app.schemas.common import Message, Page
from app.schemas.project import (
    CategoryCreate, CategoryDetail, CategoryUpdate, ProjectAdminRow, ProjectCreate,
    ProjectDetail, ProjectUpdate,
)
from app.services import analytics_service, project_service
from app.services.activity_service import record_activity

router = APIRouter(prefix="/admin", tags=["Admin - Projects"])


def _get_project(db, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise NotFoundError("Project not found")
    return project


def _unique_users(db, project_id: int) -> int:
    return db.execute(
        select(func.count(func.distinct(ProjectOpen.user_id))).where(
            ProjectOpen.project_id == project_id
        )
    ).scalar_one()


def _to_detail(db, project: Project) -> ProjectDetail:
    detail = ProjectDetail.model_validate(project)
    detail.unique_users = _unique_users(db, project.id)
    detail.allowed_employee_ids = [p.user.employee_id for p in project.permissions if p.user]
    return detail


# --------------------------------------------------------------------------
# Projects
# --------------------------------------------------------------------------
@router.get("/projects", response_model=Page[ProjectAdminRow])
def list_projects(
    admin: AdminUser,
    db: Db,
    search: Annotated[str | None, Query(max_length=200)] = None,
    category_id: int | None = None,
    status: Annotated[str | None, Query(max_length=32)] = None,
    visibility: Annotated[str | None, Query(max_length=32)] = None,
    include_inactive: bool = True,
    include_deleted: bool = False,
    sort: Annotated[str, Query(pattern="^(name|recent|updated|most_used|featured)$")] = "updated",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ProjectAdminRow]:
    stmt = project_service.build_project_query(
        db, admin, search=search, category_id=category_id, status=status,
        include_inactive=include_inactive, include_deleted=include_deleted, sort=sort,
    )
    if visibility:
        stmt = stmt.where(Project.visibility == visibility)

    total = db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    rows = db.execute(stmt.limit(limit).offset(offset)).scalars().unique().all()

    favs = project_service.favourite_ids(db, admin)
    items = []
    for project in rows:
        row = ProjectAdminRow.model_validate(project)
        row.is_favourite = project.id in favs
        row.unique_users = _unique_users(db, project.id)
        items.append(row)
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.post("/projects", response_model=ProjectDetail, status_code=201)
def create_project(payload: ProjectCreate, admin: AdminUser, db: Db, ctx: Ctx) -> ProjectDetail:
    """Add a project. It appears on the dashboard immediately — no code change."""
    if payload.category_id is not None and db.get(Category, payload.category_id) is None:
        raise ValidationError("The selected category does not exist")

    project = Project(
        name=payload.name.strip(),
        slug=project_service.unique_slug(db, Project, payload.name),
        description=payload.description,
        short_description=payload.short_description or (payload.description or "")[:280] or None,
        url=str(payload.url),
        documentation_url=str(payload.documentation_url) if payload.documentation_url else None,
        category_id=payload.category_id,
        owner_name=(payload.owner_name or admin.full_name).strip(),
        owner_user_id=payload.owner_user_id,
        icon=payload.icon,
        colour=payload.colour,
        status=str(payload.status),
        visibility=str(payload.visibility),
        allowed_departments=",".join(d.strip() for d in payload.allowed_departments if d.strip())
        or None,
        is_featured=payload.is_featured,
        open_in_new_tab=payload.open_in_new_tab,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        created_by_id=admin.id,
        updated_by_id=admin.id,
    )
    project.tags = project_service.resolve_tags(db, payload.tags)
    db.add(project)
    db.flush()

    unmatched: list[str] = []
    if payload.visibility == Visibility.SPECIFIC_EMPLOYEES:
        unmatched = project_service.sync_permissions(
            db, project, payload.allowed_employee_ids, admin
        )

    record_activity(
        db, event_type=EventType.PROJECT_CREATED, user=admin, project=project,
        description=f"Created project '{project.name}'", context=ctx,
        metadata={
            "url": project.url,
            "visibility": project.visibility,
            "unmatched_employee_ids": unmatched,
        },
    )
    db.flush()
    db.refresh(project)
    detail = _to_detail(db, project)
    return detail


@router.get("/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, admin: AdminUser, db: Db) -> ProjectDetail:
    return _to_detail(db, _get_project(db, project_id))


@router.put("/projects/{project_id}", response_model=ProjectDetail)
def update_project(
    project_id: int, payload: ProjectUpdate, admin: AdminUser, db: Db, ctx: Ctx
) -> ProjectDetail:
    project = _get_project(db, project_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return _to_detail(db, project)

    if changes.get("category_id") is not None and db.get(Category, changes["category_id"]) is None:
        raise ValidationError("The selected category does not exist")

    audit: dict[str, object] = {}
    for field, value in changes.items():
        if field in {"allowed_employee_ids", "tags"}:
            continue
        if value is None and field in {
            "name", "url", "icon", "status", "visibility", "is_featured",
            "open_in_new_tab", "sort_order", "is_active",
        }:
            continue
        if field == "name":
            project.name = value.strip()
            project.slug = project_service.unique_slug(
                db, Project, value, exclude_id=project.id
            )
        elif field in {"url", "documentation_url"}:
            setattr(project, field, str(value) if value else None)
        elif field in {"status", "visibility"}:
            setattr(project, field, str(value))
        elif field == "allowed_departments":
            project.allowed_departments = (
                ",".join(d.strip() for d in (value or []) if d.strip()) or None
            )
        else:
            setattr(project, field, value)
        audit[field] = str(value)[:120] if value is not None else None

    if "tags" in changes and changes["tags"] is not None:
        project.tags = project_service.resolve_tags(db, changes["tags"])
        audit["tags"] = changes["tags"]

    if project.visibility == Visibility.SPECIFIC_EMPLOYEES:
        if "allowed_employee_ids" in changes:
            unmatched = project_service.sync_permissions(
                db, project, changes["allowed_employee_ids"], admin
            )
            audit["unmatched_employee_ids"] = unmatched
    elif "visibility" in changes:
        # Visibility moved away from the explicit list; drop stale grants.
        for perm in list(project.permissions):
            project.permissions.remove(perm)
            db.delete(perm)

    project.updated_by_id = admin.id
    db.add(project)
    record_activity(
        db, event_type=EventType.PROJECT_UPDATED, user=admin, project=project,
        description=f"Updated project '{project.name}' ({', '.join(sorted(audit))})",
        context=ctx, metadata=audit,
    )
    db.flush()
    db.refresh(project)
    return _to_detail(db, project)


@router.post("/projects/{project_id}/duplicate", response_model=ProjectDetail, status_code=201)
def duplicate_project(project_id: int, admin: AdminUser, db: Db, ctx: Ctx) -> ProjectDetail:
    """Copy a project as an inactive draft, so the original keeps its stats."""
    source = _get_project(db, project_id)
    name = f"{source.name} (Copy)"
    clone = Project(
        name=name,
        slug=project_service.unique_slug(db, Project, name),
        description=source.description,
        short_description=source.short_description,
        url=source.url,
        documentation_url=source.documentation_url,
        category_id=source.category_id,
        owner_name=source.owner_name,
        owner_user_id=source.owner_user_id,
        icon=source.icon,
        colour=source.colour,
        status=source.status,
        visibility=source.visibility,
        allowed_departments=source.allowed_departments,
        is_featured=False,
        open_in_new_tab=source.open_in_new_tab,
        sort_order=source.sort_order,
        is_active=False,
        created_by_id=admin.id,
        updated_by_id=admin.id,
    )
    clone.tags = list(source.tags)
    db.add(clone)
    db.flush()
    record_activity(
        db, event_type=EventType.PROJECT_CREATED, user=admin, project=clone,
        description=f"Duplicated project '{source.name}' as '{clone.name}'",
        context=ctx, metadata={"source_project_id": source.id},
    )
    db.flush()
    db.refresh(clone)
    return _to_detail(db, clone)


@router.delete("/projects/{project_id}", response_model=Message)
def delete_project(project_id: int, admin: AdminUser, db: Db, ctx: Ctx) -> Message:
    """Soft delete: hidden from dashboards, retained for the audit trail."""
    project = _get_project(db, project_id)
    if project.is_deleted:
        raise ConflictError("Project is already deleted")

    project.is_deleted = True
    project.is_active = False
    project.deleted_at = utcnow()
    project.updated_by_id = admin.id
    db.add(project)
    record_activity(
        db, event_type=EventType.PROJECT_DELETED, user=admin, project=project,
        description=f"Deleted project '{project.name}'", context=ctx,
        metadata={"soft_delete": True},
    )
    return Message(
        message=f"'{project.name}' has been deleted",
        detail="Historical usage remains visible in the activity log.",
    )


@router.post("/projects/{project_id}/restore", response_model=ProjectDetail)
def restore_project(project_id: int, admin: AdminUser, db: Db, ctx: Ctx) -> ProjectDetail:
    project = _get_project(db, project_id)
    project.is_deleted = False
    project.is_active = True
    project.deleted_at = None
    project.updated_by_id = admin.id
    db.add(project)
    record_activity(
        db, event_type=EventType.PROJECT_UPDATED, user=admin, project=project,
        description=f"Restored project '{project.name}'", context=ctx,
        metadata={"restored": True},
    )
    db.flush()
    db.refresh(project)
    return _to_detail(db, project)


@router.get("/projects/{project_id}/stats", response_model=ProjectStatsResponse)
def project_stats(
    project_id: int, admin: AdminUser, db: Db,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> ProjectStatsResponse:
    _get_project(db, project_id)
    return ProjectStatsResponse(**analytics_service.project_stats(db, project_id, days))


# --------------------------------------------------------------------------
# Categories
# --------------------------------------------------------------------------
@router.get("/categories", response_model=list[CategoryDetail])
def list_categories(admin: AdminUser, db: Db) -> list[CategoryDetail]:
    counts = dict(
        db.execute(
            select(Project.category_id, func.count(Project.id))
            .where(Project.is_deleted.is_(False))
            .group_by(Project.category_id)
        ).all()
    )
    rows = db.execute(
        select(Category).order_by(Category.sort_order, Category.name)
    ).scalars().all()
    result = []
    for cat in rows:
        detail = CategoryDetail.model_validate(cat)
        detail.project_count = counts.get(cat.id, 0)
        result.append(detail)
    return result


@router.post("/categories", response_model=CategoryDetail, status_code=201)
def create_category(
    payload: CategoryCreate, admin: AdminUser, db: Db, ctx: Ctx
) -> CategoryDetail:
    if db.execute(
        select(Category.id).where(func.lower(Category.name) == payload.name.strip().lower())
    ).first():
        raise ConflictError(f"A category named '{payload.name}' already exists")

    category = Category(
        name=payload.name.strip(),
        slug=project_service.unique_slug(db, Category, payload.name),
        description=payload.description,
        icon=payload.icon,
        colour=payload.colour,
        sort_order=payload.sort_order,
    )
    db.add(category)
    db.flush()
    record_activity(
        db, event_type=EventType.CATEGORY_CREATED, user=admin,
        description=f"Created category '{category.name}'", context=ctx,
        metadata={"category_id": category.id},
    )
    return CategoryDetail.model_validate(category)


@router.put("/categories/{category_id}", response_model=CategoryDetail)
def update_category(
    category_id: int, payload: CategoryUpdate, admin: AdminUser, db: Db, ctx: Ctx
) -> CategoryDetail:
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("Category not found")

    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "name" in changes:
        clash = db.execute(
            select(Category.id).where(
                func.lower(Category.name) == changes["name"].strip().lower(),
                Category.id != category.id,
            )
        ).first()
        if clash:
            raise ConflictError("Another category already uses that name")
        category.slug = project_service.unique_slug(
            db, Category, changes["name"], exclude_id=category.id
        )
    for field, value in changes.items():
        setattr(category, field, value.strip() if isinstance(value, str) else value)
    db.add(category)
    record_activity(
        db, event_type=EventType.CATEGORY_UPDATED, user=admin,
        description=f"Updated category '{category.name}'", context=ctx, metadata=changes,
    )
    db.flush()
    return CategoryDetail.model_validate(category)


@router.delete("/categories/{category_id}", response_model=Message)
def delete_category(category_id: int, admin: AdminUser, db: Db, ctx: Ctx) -> Message:
    """Refuses while projects still reference the category."""
    category = db.get(Category, category_id)
    if category is None:
        raise NotFoundError("Category not found")

    in_use = db.execute(
        select(func.count())
        .select_from(Project)
        .where(Project.category_id == category.id, Project.is_deleted.is_(False))
    ).scalar_one()
    if in_use:
        raise ConflictError(
            f"'{category.name}' is used by {in_use} project(s). "
            "Move them to another category first."
        )

    name = category.name
    db.delete(category)
    record_activity(
        db, event_type=EventType.CATEGORY_DELETED, user=admin,
        description=f"Deleted category '{name}'", context=ctx,
    )
    return Message(message=f"Category '{name}' deleted")
