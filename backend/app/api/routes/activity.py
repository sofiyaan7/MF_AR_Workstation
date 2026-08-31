"""A user's own activity. Never exposes another employee's history."""
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.dependencies import ActiveUser, Db
from app.schemas.activity import MyActivityEntry
from app.schemas.common import Page
from app.services import activity_service

router = APIRouter(prefix="/activity", tags=["Activity"])


@router.get("/me", response_model=Page[MyActivityEntry])
def my_activity(
    user: ActiveUser,
    db: Db,
    event_type: Annotated[list[str] | None, Query()] = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[MyActivityEntry]:
    """Own activity only: ``user_id`` is taken from the session, not the request."""
    rows, total = activity_service.query_activity(
        db,
        user_id=user.id,
        event_types=event_type,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return Page(
        items=[MyActivityEntry.model_validate(r) for r in rows],
        total=total, limit=limit, offset=offset,
    )
