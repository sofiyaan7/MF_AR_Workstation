"""Authentication and authorization dependencies.

Every protected route resolves its user through :func:`get_current_user`, which
trusts only the signed cookie — never a header, body field or query parameter
supplied by the client.
"""
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session as DbSession

from app.core import security
from app.core.config import settings
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.logging_config import get_logger
from app.database.session import get_db
from app.models.enums import EventType, RoleName
from app.models.user import User
from app.services.activity_service import record_activity
from app.utils.request_context import RequestContext, get_request_context

logger = get_logger(__name__)

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


def get_context(request: Request) -> RequestContext:
    return get_request_context(request)


def _extract_access_token(request: Request) -> str | None:
    """Cookie first; a Bearer header is accepted for API clients and tests."""
    token = request.cookies.get(settings.ACCESS_COOKIE_NAME)
    if token:
        return token
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip() or None
    return None


def verify_csrf(request: Request) -> None:
    """Double-submit CSRF check for cookie-authenticated state changes.

    Skipped for Bearer-token requests, which cannot be forged by a browser
    because the header is never attached automatically.
    """
    if request.method in SAFE_METHODS:
        return
    if not request.cookies.get(settings.ACCESS_COOKIE_NAME):
        return  # Bearer auth or unauthenticated: nothing to protect against.
    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get(settings.CSRF_HEADER_NAME)
    if not security.csrf_tokens_match(cookie_token, header_token):
        raise PermissionDeniedError(
            "CSRF validation failed. Refresh the page and try again."
        )


def get_current_user(
    request: Request,
    db: Annotated[DbSession, Depends(get_db)],
) -> User:
    token = _extract_access_token(request)
    if not token:
        raise AuthenticationError("Not authenticated")

    payload = security.decode_token(token, "access")
    if not payload:
        raise AuthenticationError("Session expired. Please sign in again.")

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise AuthenticationError("Invalid session")

    user = db.get(User, user_id)
    if user is None or not user.can_login:
        # Covers a user disabled or deleted after their token was issued.
        raise AuthenticationError("This account is no longer active.")

    request.state.current_user = user
    return user


def get_current_user_csrf(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Authenticated user for state-changing routes (adds the CSRF check)."""
    verify_csrf(request)
    return user


def require_password_current(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Blocks normal use while a forced password change is outstanding."""
    if user.must_change_password:
        raise PermissionDeniedError(
            "You must change your password before continuing.",
        )
    return user


def _deny(
    request: Request, db: DbSession, user: User, what: str
) -> None:
    record_activity(
        db,
        event_type=EventType.UNAUTHORIZED_ACCESS,
        user=user,
        description=f"Denied access to {what}: {request.method} {request.url.path}",
        success=False,
        context=get_request_context(request),
        metadata={"path": request.url.path, "method": request.method, "role": user.role_name},
        commit=True,
    )
    logger.warning(
        "Authorization denied user_id=%s role=%s path=%s",
        user.id, user.role_name, request.url.path,
    )
    raise PermissionDeniedError("You do not have permission to perform this action.")


def require_admin(
    request: Request,
    db: Annotated[DbSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Gate for every /api/admin route. Denials are audited."""
    if not user.is_admin:
        _deny(request, db, user, "an administrator area")
    verify_csrf(request)
    return user


def require_super_admin(
    request: Request,
    db: Annotated[DbSession, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_super_admin:
        _deny(request, db, user, "a super-administrator action")
    verify_csrf(request)
    return user


# Convenience aliases used throughout the route modules.
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserCsrf = Annotated[User, Depends(get_current_user_csrf)]
ActiveUser = Annotated[User, Depends(require_password_current)]
AdminUser = Annotated[User, Depends(require_admin)]
SuperAdminUser = Annotated[User, Depends(require_super_admin)]
Db = Annotated[DbSession, Depends(get_db)]
Ctx = Annotated[RequestContext, Depends(get_context)]

__all__ = [
    "CurrentUser", "CurrentUserCsrf", "ActiveUser", "AdminUser", "SuperAdminUser",
    "Db", "Ctx", "get_current_user", "require_admin", "require_super_admin",
    "verify_csrf", "RoleName",
]
