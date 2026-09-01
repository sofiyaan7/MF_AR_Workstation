"""Per-project change suggestions.

Any employee who can see a project may raise a suggestion against it and read
every suggestion on it — the log is shared on purpose. Closing and reopening is
restricted to the author and to admins, so the status column stays meaningful.
"""
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.auth.dependencies import ActiveUser, Ctx, Db
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.database.base import utcnow
from app.models.enums import EventType, SuggestionStatus
from app.models.suggestion import Suggestion
from app.schemas.suggestion import (
    SuggestionCounts, SuggestionCreate, SuggestionList, SuggestionRead,
    SuggestionStatusUpdate,
)
from app.services import project_service
from app.services.activity_service import record_activity, touch_last_activity

router = APIRouter(prefix="/projects", tags=["Suggestions"])


def _can_manage(user, suggestion: Suggestion) -> bool:
    """Authors close their own; admins close anyone's."""
    return bool(user.is_admin or (suggestion.user_id and suggestion.user_id == user.id))


def _to_read(user, suggestion: Suggestion) -> SuggestionRead:
    read = SuggestionRead.model_validate(suggestion)
    read.can_manage = _can_manage(user, suggestion)
    return read


def _get_for_project(db, user, project_id: int, suggestion_id: int) -> Suggestion:
    # Resolve the project first so project visibility governs the suggestion:
    # a user who cannot see the project must not reach its suggestions.
    project_service.get_visible_project(db, user, project_id)
    suggestion = db.get(Suggestion, suggestion_id)
    if suggestion is None or suggestion.project_id != project_id:
        raise NotFoundError("Suggestion not found")
    return suggestion


@router.get("/{project_id}/suggestions", response_model=SuggestionList)
def list_suggestions(
    project_id: int,
    user: ActiveUser,
    db: Db,
    status: Annotated[str | None, Query(pattern="^(OPEN|CLOSED)$")] = None,
) -> SuggestionList:
    """Every suggestion on a project, newest first, with open/closed totals."""
    project_service.get_visible_project(db, user, project_id)

    stmt = select(Suggestion).where(Suggestion.project_id == project_id)
    if status:
        stmt = stmt.where(Suggestion.status == status)
    rows = db.execute(stmt.order_by(Suggestion.created_at.desc())).scalars().unique().all()

    # Counts always describe the whole project, not the filtered view, so the
    # tab labels do not change when a filter is applied.
    tally = dict(
        db.execute(
            select(Suggestion.status, func.count())
            .where(Suggestion.project_id == project_id)
            .group_by(Suggestion.status)
        ).all()
    )
    counts = SuggestionCounts(
        open=tally.get(str(SuggestionStatus.OPEN), 0),
        closed=tally.get(str(SuggestionStatus.CLOSED), 0),
        total=sum(tally.values()),
    )
    return SuggestionList(items=[_to_read(user, s) for s in rows], counts=counts)


@router.post("/{project_id}/suggestions", response_model=SuggestionRead, status_code=201)
def create_suggestion(
    project_id: int, payload: SuggestionCreate, user: ActiveUser, db: Db, ctx: Ctx
) -> SuggestionRead:
    project = project_service.get_visible_project(db, user, project_id)

    suggestion = Suggestion(
        project_id=project.id,
        user_id=user.id,
        title=payload.title.strip(),
        body=(payload.body or "").strip() or None,
        status=str(SuggestionStatus.OPEN),
    )
    db.add(suggestion)
    db.flush()

    record_activity(
        db, event_type=EventType.SUGGESTION_CREATED, user=user, project=project,
        description=f"Suggested '{suggestion.title}' on '{project.name}'", context=ctx,
    )
    touch_last_activity(db, user)
    db.refresh(suggestion)
    return _to_read(user, suggestion)


@router.patch("/{project_id}/suggestions/{suggestion_id}", response_model=SuggestionRead)
def set_suggestion_status(
    project_id: int,
    suggestion_id: int,
    payload: SuggestionStatusUpdate,
    user: ActiveUser,
    db: Db,
    ctx: Ctx,
) -> SuggestionRead:
    """Close or reopen a suggestion. Author or admin only."""
    suggestion = _get_for_project(db, user, project_id, suggestion_id)
    if not _can_manage(user, suggestion):
        raise PermissionDeniedError(
            "Only the person who raised this suggestion, or an administrator, can change it"
        )

    target = str(payload.status)
    if target == suggestion.status:
        return _to_read(user, suggestion)

    if target == str(SuggestionStatus.CLOSED):
        suggestion.status = target
        suggestion.closed_at = utcnow()
        suggestion.closed_by_id = user.id
        event = EventType.SUGGESTION_CLOSED
        verb = "Closed"
    else:
        suggestion.status = target
        suggestion.closed_at = None
        suggestion.closed_by_id = None
        event = EventType.SUGGESTION_REOPENED
        verb = "Reopened"

    db.flush()
    record_activity(
        db, event_type=event, user=user, project=suggestion.project,
        description=f"{verb} suggestion '{suggestion.title}'", context=ctx,
    )
    touch_last_activity(db, user)
    db.refresh(suggestion)
    return _to_read(user, suggestion)
