"""Suggestion schemas."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import SuggestionStatus
from app.schemas.common import ORMModel


class SuggestionAuthor(ORMModel):
    id: int
    employee_id: str
    full_name: str


class SuggestionRead(ORMModel):
    id: int
    project_id: int
    title: str
    body: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
    closed_at: datetime | None = None
    # Null when the account has since been deleted; the suggestion survives it.
    user: SuggestionAuthor | None = None
    closed_by: SuggestionAuthor | None = None

    # Set per request: whether the caller may close or reopen this one.
    can_manage: bool = False


class SuggestionCreate(BaseModel):
    title: str = Field(min_length=4, max_length=200)
    body: str | None = Field(default=None, max_length=5000)


class SuggestionCounts(BaseModel):
    open: int = 0
    closed: int = 0
    total: int = 0


class SuggestionList(BaseModel):
    items: list[SuggestionRead]
    counts: SuggestionCounts


class SuggestionStatusUpdate(BaseModel):
    status: SuggestionStatus
