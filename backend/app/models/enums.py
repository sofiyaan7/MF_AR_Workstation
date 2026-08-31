"""String enums used across the schema.

Stored as plain VARCHAR rather than native database enums so that new values
(e.g. a future SSO role or project status) can be introduced without a
type-altering migration.
"""
from enum import Enum


class StrEnum(str, Enum):
    """`enum.StrEnum` backport (Python 3.10 compatible).

    Overriding ``__str__`` matters: the stdlib default renders ``ClassName.MEMBER``
    which would leak into f-strings, JSON and log lines.
    """

    __str__ = str.__str__

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return str.__repr__(self)


class RoleName(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"


class AccountStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    LOCKED = "LOCKED"
    PENDING_PASSWORD_CHANGE = "PENDING_PASSWORD_CHANGE"


class ProjectStatus(StrEnum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    DEPRECATED = "DEPRECATED"
    COMING_SOON = "COMING_SOON"


class Visibility(StrEnum):
    ALL_EMPLOYEES = "ALL_EMPLOYEES"
    SPECIFIC_EMPLOYEES = "SPECIFIC_EMPLOYEES"
    ADMIN_ONLY = "ADMIN_ONLY"


class EventType(StrEnum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    FAILED_LOGIN = "FAILED_LOGIN"
    TOKEN_REFRESHED = "TOKEN_REFRESHED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    PROJECT_VIEWED = "PROJECT_VIEWED"
    PROJECT_OPENED = "PROJECT_OPENED"
    PROJECT_FAVOURITED = "PROJECT_FAVOURITED"
    PROJECT_UNFAVOURITED = "PROJECT_UNFAVOURITED"
    PROFILE_UPDATED = "PROFILE_UPDATED"
    PROJECT_CREATED = "PROJECT_CREATED"
    PROJECT_UPDATED = "PROJECT_UPDATED"
    PROJECT_DELETED = "PROJECT_DELETED"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    USER_DISABLED = "USER_DISABLED"
    USER_ENABLED = "USER_ENABLED"
    USER_DELETED = "USER_DELETED"
    ROLE_CHANGED = "ROLE_CHANGED"
    CATEGORY_CREATED = "CATEGORY_CREATED"
    CATEGORY_UPDATED = "CATEGORY_UPDATED"
    CATEGORY_DELETED = "CATEGORY_DELETED"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"


ADMIN_ROLES = frozenset({RoleName.ADMIN, RoleName.SUPER_ADMIN})
