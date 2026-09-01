"""Import every model so Alembic autogenerate and Base.metadata see them all."""
from app.models.activity import ActivityLog
from app.models.enums import (
    ADMIN_ROLES, AccountStatus, EventType, ProjectStatus, RoleName, SuggestionStatus,
    Visibility,
)
from app.models.project import (
    Category, Favourite, Project, ProjectOpen, Tag, UserProjectPermission, project_tags,
)
from app.models.suggestion import Suggestion
from app.models.user import LoginAttempt, PasswordHistory, Role, Session, User

__all__ = [
    "ActivityLog", "Category", "Favourite", "Project", "ProjectOpen", "Tag",
    "UserProjectPermission", "project_tags", "LoginAttempt", "PasswordHistory",
    "Role", "Session", "User", "RoleName", "AccountStatus", "ProjectStatus",
    "Visibility", "EventType", "ADMIN_ROLES", "Suggestion", "SuggestionStatus",
]
