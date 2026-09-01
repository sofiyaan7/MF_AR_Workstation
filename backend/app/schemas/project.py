"""Project, category and tag schemas."""
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.enums import ProjectStatus, Visibility
from app.schemas.common import ORMModel


class CategoryRef(ORMModel):
    id: int
    name: str
    slug: str
    icon: str | None = None
    colour: str | None = None


class CategoryDetail(CategoryRef):
    description: str | None = None
    sort_order: int
    is_active: bool
    created_at: datetime
    project_count: int = 0


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=64)
    colour: str | None = Field(default=None, max_length=24)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    icon: str | None = Field(default=None, max_length=64)
    colour: str | None = Field(default=None, max_length=24)
    sort_order: int | None = None
    is_active: bool | None = None


class TagRef(ORMModel):
    id: int
    name: str
    slug: str


class ProjectCard(ORMModel):
    """Shape used by every project list in the UI."""

    id: int
    name: str
    slug: str
    short_description: str | None = None
    description: str | None = None
    url: str
    icon: str
    colour: str | None = None
    status: str
    visibility: str
    owner_name: str | None = None
    is_featured: bool
    open_in_new_tab: bool
    total_opens: int
    created_at: datetime
    updated_at: datetime
    last_opened_at: datetime | None = None
    category: CategoryRef | None = None
    tags: list[TagRef] = []

    # Per-request annotations, set by the route for the calling user.
    is_favourite: bool = False
    my_open_count: int = 0
    my_last_opened_at: datetime | None = None


class ProjectDetail(ProjectCard):
    documentation_url: str | None = None
    sort_order: int
    is_active: bool
    created_by_id: int | None = None
    updated_by_id: int | None = None
    unique_users: int = 0
    allowed_employee_ids: list[str] = []
    # Sourced from Project.department_list, which splits the stored CSV column.
    allowed_departments: list[str] = Field(
        default_factory=list, validation_alias="department_list"
    )


class ProjectAdminRow(ProjectCard):
    is_active: bool
    is_deleted: bool
    unique_users: int = 0
    sort_order: int
    repository_url: str | None = None


class ProjectAdminDetail(ProjectDetail):
    """ProjectDetail plus admin-only fields.

    ``ProjectDetail`` is also returned by the employee route, so the repository
    link lives here instead: internal source URLs stay inside the admin console.
    """

    repository_url: str | None = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    url: HttpUrl
    description: str | None = Field(default=None, max_length=5000)
    short_description: str | None = Field(default=None, max_length=280)
    documentation_url: HttpUrl | None = None
    repository_url: HttpUrl | None = None
    category_id: int | None = None
    tags: list[str] = Field(default_factory=list, max_length=20)
    owner_name: str | None = Field(default=None, max_length=160)
    owner_user_id: int | None = None
    icon: str = Field(default="LayoutDashboard", max_length=64)
    colour: str | None = Field(default=None, max_length=24)
    status: ProjectStatus = ProjectStatus.ACTIVE
    visibility: Visibility = Visibility.ALL_EMPLOYEES
    allowed_employee_ids: list[str] = Field(default_factory=list, max_length=500)
    allowed_departments: list[str] = Field(default_factory=list, max_length=50)
    is_featured: bool = False
    open_in_new_tab: bool = True
    sort_order: int = 0
    is_active: bool = True

    @field_validator("url", "documentation_url", "repository_url")
    @classmethod
    def _http_only(cls, v: HttpUrl | None) -> HttpUrl | None:
        # Blocks javascript:, data: and other schemes that would be XSS vectors
        # once rendered into an anchor href by the frontend.
        if v is not None and v.scheme not in {"http", "https"}:
            raise ValueError("Project URL must use http or https")
        return v

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, v: list[str]) -> list[str]:
        return [t.strip() for t in v if t and t.strip()][:20]


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    url: HttpUrl | None = None
    description: str | None = Field(default=None, max_length=5000)
    short_description: str | None = Field(default=None, max_length=280)
    documentation_url: HttpUrl | None = None
    repository_url: HttpUrl | None = None
    category_id: int | None = None
    tags: list[str] | None = Field(default=None, max_length=20)
    owner_name: str | None = Field(default=None, max_length=160)
    owner_user_id: int | None = None
    icon: str | None = Field(default=None, max_length=64)
    colour: str | None = Field(default=None, max_length=24)
    status: ProjectStatus | None = None
    visibility: Visibility | None = None
    allowed_employee_ids: list[str] | None = None
    allowed_departments: list[str] | None = None
    is_featured: bool | None = None
    open_in_new_tab: bool | None = None
    sort_order: int | None = None
    is_active: bool | None = None

    @field_validator("url", "documentation_url", "repository_url")
    @classmethod
    def _http_only(cls, v: HttpUrl | None) -> HttpUrl | None:
        if v is not None and v.scheme not in {"http", "https"}:
            raise ValueError("Project URL must use http or https")
        return v


class ProjectOpenResponse(BaseModel):
    project_id: int
    url: str
    open_in_new_tab: bool
    message: str = "Launch recorded"


class RecentProject(BaseModel):
    project: ProjectCard
    last_opened_at: datetime


class DashboardResponse(BaseModel):
    featured: list[ProjectCard]
    recent_projects: list[RecentProject]
    favourites: list[ProjectCard]
    recently_added: list[ProjectCard]
    categories: list[CategoryDetail]
    total_projects: int
