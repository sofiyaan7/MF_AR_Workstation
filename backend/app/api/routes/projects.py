"""Employee-facing project endpoints. All results are visibility-filtered."""
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.auth.dependencies import ActiveUser, Ctx, CurrentUserCsrf, Db
from app.models.enums import EventType
from app.models.project import Category, Project, ProjectOpen, Tag
from app.schemas.common import Message, Page
from app.schemas.project import (
    CategoryDetail, DashboardResponse, ProjectCard, ProjectDetail, ProjectOpenResponse,
    RecentProject, TagRef,
)
from app.services import project_service
from app.services.activity_service import record_activity, touch_last_activity

router = APIRouter(prefix="/projects", tags=["Projects"])


def _decorate(db, user, projects: list[Project]) -> list[ProjectCard]:
    """Attach the calling user's favourite / usage annotations to each card."""
    if not projects:
        return []
    ids = [p.id for p in projects]
    favs = project_service.favourite_ids(db, user)
    last_opened = project_service.last_opened_map(db, user, ids)
    my_counts = project_service.open_counts_for_user(db, user, ids)

    cards = []
    for project in projects:
        card = ProjectCard.model_validate(project)
        card.is_favourite = project.id in favs
        card.my_open_count = my_counts.get(project.id, 0)
        card.my_last_opened_at = last_opened.get(project.id)
        cards.append(card)
    return cards


@router.get("", response_model=Page[ProjectCard])
def list_projects(
    user: ActiveUser,
    db: Db,
    search: Annotated[str | None, Query(max_length=200)] = None,
    category_id: int | None = None,
    category: Annotated[str | None, Query(max_length=80)] = None,
    tag: Annotated[list[str] | None, Query()] = None,
    owner: Annotated[str | None, Query(max_length=160)] = None,
    status: Annotated[str | None, Query(max_length=32)] = None,
    featured: bool | None = None,
    favourites_only: bool = False,
    sort: Annotated[str, Query(pattern="^(name|recent|updated|most_used|featured)$")] = "featured",
    limit: Annotated[int, Query(ge=1, le=200)] = 60,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ProjectCard]:
    """Search, filter and sort the projects this employee is allowed to see."""
    projects, total = project_service.list_projects(
        db, user,
        limit=limit, offset=offset, search=search, category_id=category_id,
        category_slug=category, tags=tag, owner=owner, status=status,
        featured=featured, favourites_only=favourites_only, sort=sort,
    )
    touch_last_activity(db, user)
    return Page(items=_decorate(db, user, projects), total=total, limit=limit, offset=offset)


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard(user: ActiveUser, db: Db) -> DashboardResponse:
    """Everything the landing page needs, in a single round trip."""
    featured, _ = project_service.list_projects(
        db, user, limit=8, featured=True, sort="featured"
    )
    recently_added, total = project_service.list_projects(db, user, limit=8, sort="recent")
    favourites, _ = project_service.list_projects(
        db, user, limit=12, favourites_only=True, sort="name"
    )
    recents = project_service.recently_opened(db, user, limit=6)

    recent_cards = _decorate(db, user, [p for p, _ in recents])
    recent_items = [
        RecentProject(project=card, last_opened_at=ts)
        for card, (_, ts) in zip(recent_cards, recents)
    ]

    counts = dict(
        db.execute(
            select(Project.category_id, func.count(Project.id))
            .where(Project.is_deleted.is_(False), Project.is_active.is_(True))
            .group_by(Project.category_id)
        ).all()
    )
    categories = db.execute(
        select(Category).where(Category.is_active.is_(True)).order_by(
            Category.sort_order, Category.name
        )
    ).scalars().all()
    category_details = []
    for cat in categories:
        detail = CategoryDetail.model_validate(cat)
        detail.project_count = counts.get(cat.id, 0)
        category_details.append(detail)

    touch_last_activity(db, user)
    return DashboardResponse(
        featured=_decorate(db, user, featured),
        recent_projects=recent_items,
        favourites=_decorate(db, user, favourites),
        recently_added=_decorate(db, user, recently_added),
        categories=category_details,
        total_projects=total,
    )


@router.get("/recent", response_model=list[RecentProject])
def recent(user: ActiveUser, db: Db, limit: Annotated[int, Query(ge=1, le=50)] = 20):
    recents = project_service.recently_opened(db, user, limit=limit)
    cards = _decorate(db, user, [p for p, _ in recents])
    return [
        RecentProject(project=card, last_opened_at=ts)
        for card, (_, ts) in zip(cards, recents)
    ]


@router.get("/favourites", response_model=list[ProjectCard])
def favourites(user: ActiveUser, db: Db) -> list[ProjectCard]:
    projects, _ = project_service.list_projects(
        db, user, limit=200, favourites_only=True, sort="name"
    )
    return _decorate(db, user, projects)


@router.get("/categories", response_model=list[CategoryDetail])
def categories(user: ActiveUser, db: Db) -> list[CategoryDetail]:
    counts = dict(
        db.execute(
            select(Project.category_id, func.count(Project.id))
            .where(Project.is_deleted.is_(False), Project.is_active.is_(True))
            .group_by(Project.category_id)
        ).all()
    )
    rows = db.execute(
        select(Category).where(Category.is_active.is_(True)).order_by(
            Category.sort_order, Category.name
        )
    ).scalars().all()
    result = []
    for cat in rows:
        detail = CategoryDetail.model_validate(cat)
        detail.project_count = counts.get(cat.id, 0)
        result.append(detail)
    return result


@router.get("/tags", response_model=list[TagRef])
def tags(user: ActiveUser, db: Db) -> list[TagRef]:
    """Tags that appear on at least one project visible to this user."""
    visible_ids = select(Project.id).where(
        Project.is_deleted.is_(False), Project.is_active.is_(True)
    )
    vis = project_service.visibility_filter(user)
    if vis is not None:
        visible_ids = visible_ids.where(vis)
    rows = db.execute(
        select(Tag)
        .where(Tag.projects.any(Project.id.in_(visible_ids)))
        .order_by(Tag.name)
    ).scalars().unique().all()
    return [TagRef.model_validate(t) for t in rows]


@router.get("/owners", response_model=list[str])
def owners(user: ActiveUser, db: Db) -> list[str]:
    stmt = select(Project.owner_name).where(
        Project.is_deleted.is_(False),
        Project.is_active.is_(True),
        Project.owner_name.isnot(None),
    ).distinct()
    vis = project_service.visibility_filter(user)
    if vis is not None:
        stmt = stmt.where(vis)
    return sorted({row[0] for row in db.execute(stmt).all() if row[0]})


@router.get("/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, user: ActiveUser, db: Db, ctx: Ctx) -> ProjectDetail:
    """Project detail page. Viewing is audited separately from opening."""
    project = project_service.get_visible_project(db, user, project_id)

    detail = ProjectDetail.model_validate(project)
    detail.is_favourite = project.id in project_service.favourite_ids(db, user)
    detail.my_open_count = project_service.open_counts_for_user(db, user, [project.id]).get(
        project.id, 0
    )
    detail.my_last_opened_at = project_service.last_opened_map(db, user, [project.id]).get(
        project.id
    )
    detail.unique_users = db.execute(
        select(func.count(func.distinct(ProjectOpen.user_id))).where(
            ProjectOpen.project_id == project.id
        )
    ).scalar_one()
    if user.is_admin:
        detail.allowed_employee_ids = [
            perm.user.employee_id for perm in project.permissions if perm.user
        ]

    record_activity(
        db, event_type=EventType.PROJECT_VIEWED, user=user, project=project,
        description=f"Viewed project '{project.name}'", context=ctx,
    )
    touch_last_activity(db, user)
    return detail


@router.post("/{project_id}/open", response_model=ProjectOpenResponse)
def open_project(project_id: int, user: CurrentUserCsrf, db: Db, ctx: Ctx) -> ProjectOpenResponse:
    """Record a launch and return the URL for the client to navigate to."""
    project = project_service.get_visible_project(db, user, project_id)
    project_service.record_open(db, user, project, ctx)
    return ProjectOpenResponse(
        project_id=project.id,
        url=project.url,
        open_in_new_tab=project.open_in_new_tab,
        message=f"Opening {project.name}",
    )


@router.post("/{project_id}/favourite", response_model=Message)
def add_favourite(project_id: int, user: CurrentUserCsrf, db: Db, ctx: Ctx) -> Message:
    project = project_service.get_visible_project(db, user, project_id)
    project_service.add_favourite(db, user, project, ctx)
    return Message(message=f"Added '{project.name}' to your favourites")


@router.delete("/{project_id}/favourite", response_model=Message)
def remove_favourite(project_id: int, user: CurrentUserCsrf, db: Db, ctx: Ctx) -> Message:
    project = project_service.get_visible_project(db, user, project_id)
    project_service.remove_favourite(db, user, project, ctx)
    return Message(message=f"Removed '{project.name}' from your favourites")
