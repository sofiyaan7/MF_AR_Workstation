"""Project queries, visibility enforcement, favourites and open tracking."""
import re
import unicodedata
from datetime import datetime
from typing import Iterable, Sequence

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session as DbSession

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.database.base import utcnow
from app.models.enums import EventType, ProjectStatus, Visibility
from app.models.project import (
    Category, Favourite, Project, ProjectOpen, Tag, UserProjectPermission,
)
from app.models.user import User
from app.services.activity_service import record_activity
from app.utils.request_context import RequestContext


# --------------------------------------------------------------------------
# Slugs
# --------------------------------------------------------------------------
def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value) or "item"


def unique_slug(db: DbSession, model, base: str, *, exclude_id: int | None = None) -> str:
    slug = slugify(base)
    candidate = slug
    suffix = 2
    while True:
        stmt = select(model.id).where(model.slug == candidate)
        if exclude_id is not None:
            stmt = stmt.where(model.id != exclude_id)
        if db.execute(stmt).first() is None:
            return candidate
        candidate = f"{slug}-{suffix}"
        suffix += 1


# --------------------------------------------------------------------------
# Visibility
# --------------------------------------------------------------------------
def visibility_filter(user: User):
    """SQL predicate restricting projects to those ``user`` may see.

    This is the single source of truth for read access and is applied to every
    project query, including search, favourites and recents. Admins see all.
    """
    if user.is_admin:
        return None

    granted_ids = select(UserProjectPermission.project_id).where(
        UserProjectPermission.user_id == user.id
    )
    department_clauses = []
    if user.department:
        # allowed_departments is a comma-separated list; match with padding so
        # "Research" does not match "Research Ops".
        department_clauses.append(
            func.lower("," + func.coalesce(Project.allowed_departments, "") + ",").like(
                f"%,{user.department.strip().lower()},%"
            )
        )

    all_employees = Project.visibility == Visibility.ALL_EMPLOYEES
    if department_clauses:
        all_employees = and_(
            Project.visibility == Visibility.ALL_EMPLOYEES,
            or_(
                Project.allowed_departments.is_(None),
                Project.allowed_departments == "",
                *department_clauses,
            ),
        )
    else:
        all_employees = and_(
            Project.visibility == Visibility.ALL_EMPLOYEES,
            or_(Project.allowed_departments.is_(None), Project.allowed_departments == ""),
        )

    return or_(
        all_employees,
        and_(
            Project.visibility == Visibility.SPECIFIC_EMPLOYEES,
            Project.id.in_(granted_ids),
        ),
    )


def user_can_access(db: DbSession, user: User, project: Project) -> bool:
    """Authoritative per-object check, mirrored by :func:`visibility_filter`."""
    if project.is_deleted and not user.is_admin:
        return False
    if not project.is_active and not user.is_admin:
        return False
    if user.is_admin:
        return True
    if project.visibility == Visibility.ADMIN_ONLY:
        return False
    if project.visibility == Visibility.SPECIFIC_EMPLOYEES:
        return (
            db.execute(
                select(UserProjectPermission.id).where(
                    UserProjectPermission.user_id == user.id,
                    UserProjectPermission.project_id == project.id,
                )
            ).first()
            is not None
        )
    departments = project.department_list
    if departments:
        return bool(user.department) and user.department.strip().lower() in {
            d.lower() for d in departments
        }
    return True


def get_visible_project(db: DbSession, user: User, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None or (project.is_deleted and not user.is_admin):
        raise NotFoundError("Project not found")
    if not user_can_access(db, user, project):
        # 404 rather than 403: do not confirm that a hidden project exists.
        raise NotFoundError("Project not found")
    return project


# --------------------------------------------------------------------------
# Listing / search
# --------------------------------------------------------------------------
SORT_OPTIONS = {
    "name": (Project.name.asc(),),
    "recent": (Project.created_at.desc(),),
    "updated": (Project.updated_at.desc(),),
    "most_used": (Project.total_opens.desc(), Project.name.asc()),
    "featured": (Project.is_featured.desc(), Project.sort_order.asc(), Project.name.asc()),
}


def build_project_query(
    db: DbSession,
    user: User,
    *,
    search: str | None = None,
    category_id: int | None = None,
    category_slug: str | None = None,
    tags: Sequence[str] | None = None,
    owner: str | None = None,
    status: str | None = None,
    featured: bool | None = None,
    favourites_only: bool = False,
    include_inactive: bool = False,
    include_deleted: bool = False,
    sort: str = "featured",
) -> Select:
    stmt = select(Project)

    if not include_deleted or not user.is_admin:
        stmt = stmt.where(Project.is_deleted.is_(False))
    if not include_inactive or not user.is_admin:
        stmt = stmt.where(Project.is_active.is_(True))

    vis = visibility_filter(user)
    if vis is not None:
        stmt = stmt.where(vis)

    if search:
        pattern = f"%{search.strip()}%"
        tag_match = select(Tag.id).where(Tag.name.ilike(pattern))
        stmt = stmt.where(
            or_(
                Project.name.ilike(pattern),
                Project.description.ilike(pattern),
                Project.short_description.ilike(pattern),
                Project.owner_name.ilike(pattern),
                Project.category.has(Category.name.ilike(pattern)),
                Project.tags.any(Tag.id.in_(tag_match)),
            )
        )
    if category_id is not None:
        stmt = stmt.where(Project.category_id == category_id)
    if category_slug:
        stmt = stmt.where(Project.category.has(Category.slug == category_slug))
    if tags:
        for tag in tags:
            stmt = stmt.where(Project.tags.any(func.lower(Tag.name) == tag.strip().lower()))
    if owner:
        stmt = stmt.where(Project.owner_name.ilike(f"%{owner.strip()}%"))
    if status:
        stmt = stmt.where(Project.status == status)
    if featured is not None:
        stmt = stmt.where(Project.is_featured.is_(featured))
    if favourites_only:
        fav_ids = select(Favourite.project_id).where(Favourite.user_id == user.id)
        stmt = stmt.where(Project.id.in_(fav_ids))

    order = SORT_OPTIONS.get(sort, SORT_OPTIONS["featured"])
    return stmt.order_by(*order)


def list_projects(
    db: DbSession, user: User, *, limit: int = 100, offset: int = 0, **filters
) -> tuple[list[Project], int]:
    stmt = build_project_query(db, user, **filters)
    total = db.execute(
        select(func.count()).select_from(stmt.order_by(None).subquery())
    ).scalar_one()
    rows = list(db.execute(stmt.limit(limit).offset(offset)).scalars().unique())
    return rows, total


def favourite_ids(db: DbSession, user: User) -> set[int]:
    return set(
        db.execute(select(Favourite.project_id).where(Favourite.user_id == user.id))
        .scalars()
        .all()
    )


def last_opened_map(db: DbSession, user: User, project_ids: Iterable[int]) -> dict[int, datetime]:
    ids = list(project_ids)
    if not ids:
        return {}
    rows = db.execute(
        select(ProjectOpen.project_id, func.max(ProjectOpen.opened_at))
        .where(ProjectOpen.user_id == user.id, ProjectOpen.project_id.in_(ids))
        .group_by(ProjectOpen.project_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def open_counts_for_user(db: DbSession, user: User, project_ids: Iterable[int]) -> dict[int, int]:
    ids = list(project_ids)
    if not ids:
        return {}
    rows = db.execute(
        select(ProjectOpen.project_id, func.count(ProjectOpen.id))
        .where(ProjectOpen.user_id == user.id, ProjectOpen.project_id.in_(ids))
        .group_by(ProjectOpen.project_id)
    ).all()
    return {row[0]: row[1] for row in rows}


def recently_opened(db: DbSession, user: User, limit: int = 8) -> list[tuple[Project, datetime]]:
    """Most recent distinct projects this user opened, newest first."""
    stmt = (
        select(ProjectOpen.project_id, func.max(ProjectOpen.opened_at).label("last_opened"))
        .where(ProjectOpen.user_id == user.id)
        .group_by(ProjectOpen.project_id)
        .order_by(func.max(ProjectOpen.opened_at).desc())
        .limit(limit * 3)
    )
    rows = db.execute(stmt).all()
    if not rows:
        return []
    ordered = {row[0]: row[1] for row in rows}

    visible_stmt = select(Project).where(
        Project.id.in_(list(ordered)),
        Project.is_deleted.is_(False),
        Project.is_active.is_(True),
    )
    vis = visibility_filter(user)
    if vis is not None:
        visible_stmt = visible_stmt.where(vis)

    projects = {p.id: p for p in db.execute(visible_stmt).scalars().unique()}
    result = [(projects[pid], ts) for pid, ts in ordered.items() if pid in projects]
    return result[:limit]


# --------------------------------------------------------------------------
# Mutations
# --------------------------------------------------------------------------
def resolve_tags(db: DbSession, names: Sequence[str] | None) -> list[Tag]:
    """Find-or-create tags, matched case-insensitively."""
    if not names:
        return []
    tags: list[Tag] = []
    seen: set[str] = set()
    for raw in names:
        name = (raw or "").strip()
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        tag = db.execute(
            select(Tag).where(func.lower(Tag.name) == name.lower())
        ).scalars().first()
        if tag is None:
            tag = Tag(name=name, slug=unique_slug(db, Tag, name))
            db.add(tag)
            db.flush()
        tags.append(tag)
    return tags


def sync_permissions(
    db: DbSession, project: Project, employee_ids: Sequence[str] | None, granted_by: User
) -> list[str]:
    """Replace the project's explicit grants. Returns unmatched employee IDs."""
    wanted = [e.strip() for e in (employee_ids or []) if e and e.strip()]
    users = (
        db.execute(
            select(User).where(
                func.lower(User.employee_id).in_([e.lower() for e in wanted]),
                User.is_deleted.is_(False),
            )
        ).scalars().all()
        if wanted
        else []
    )
    found = {u.employee_id.lower(): u for u in users}
    unmatched = [e for e in wanted if e.lower() not in found]

    existing = {p.user_id: p for p in project.permissions}
    keep_ids = {u.id for u in users}

    for user_id, perm in list(existing.items()):
        if user_id not in keep_ids:
            project.permissions.remove(perm)
            db.delete(perm)

    for user in users:
        if user.id not in existing:
            project.permissions.append(
                UserProjectPermission(
                    user_id=user.id, granted_by_id=granted_by.id, granted_at=utcnow()
                )
            )
    db.flush()
    return unmatched


def record_open(
    db: DbSession, user: User, project: Project, context: RequestContext | None = None
) -> None:
    """Log a launch: counters, per-open row and an audit entry."""
    if project.status == ProjectStatus.COMING_SOON:
        raise PermissionDeniedError("This project is not available yet.")

    db.add(ProjectOpen(user_id=user.id, project_id=project.id, opened_at=utcnow()))
    project.total_opens += 1
    project.last_opened_at = utcnow()
    user.last_activity_at = utcnow()
    db.add(project)
    db.add(user)
    record_activity(
        db,
        event_type=EventType.PROJECT_OPENED,
        user=user,
        project=project,
        description=f"Opened project '{project.name}'",
        context=context,
        metadata={"url": project.url},
    )


def add_favourite(
    db: DbSession, user: User, project: Project, context: RequestContext | None = None
) -> None:
    existing = db.execute(
        select(Favourite).where(
            Favourite.user_id == user.id, Favourite.project_id == project.id
        )
    ).scalars().first()
    if existing:
        raise ConflictError("Project is already in your favourites")
    db.add(Favourite(user_id=user.id, project_id=project.id, created_at=utcnow()))
    record_activity(
        db,
        event_type=EventType.PROJECT_FAVOURITED,
        user=user,
        project=project,
        description=f"Added '{project.name}' to favourites",
        context=context,
    )


def remove_favourite(
    db: DbSession, user: User, project: Project, context: RequestContext | None = None
) -> None:
    existing = db.execute(
        select(Favourite).where(
            Favourite.user_id == user.id, Favourite.project_id == project.id
        )
    ).scalars().first()
    if not existing:
        raise NotFoundError("Project is not in your favourites")
    db.delete(existing)
    record_activity(
        db,
        event_type=EventType.PROJECT_UNFAVOURITED,
        user=user,
        project=project,
        description=f"Removed '{project.name}' from favourites",
        context=context,
    )
