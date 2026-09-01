"""Authentication endpoints."""
from fastapi import APIRouter, Request, Response, status

from app.auth.dependencies import Ctx, CurrentUser, CurrentUserCsrf, Db
from app.core.config import settings
from app.core.exceptions import AuthenticationError, ValidationError
from app.core.password_policy import describe_policy
from app.models.enums import EventType
from app.schemas.auth import (
    ChangePasswordRequest, ForgotPasswordRequest, LoginRequest, LoginResponse,
    PasswordPolicyResponse,
)
from app.schemas.common import Message
from app.schemas.user import ProfileUpdate, UserProfile
from app.services import auth_service
from app.services.activity_service import record_activity
from app.utils.request_context import clear_auth_cookies, set_auth_cookies

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Db, ctx: Ctx) -> LoginResponse:
    """Exchange Employee ID + password for an authenticated session."""
    user = auth_service.authenticate(db, payload.username, payload.password, ctx)
    access, refresh, csrf = auth_service.issue_session(db, user, ctx)
    set_auth_cookies(response, access, refresh, csrf)
    return LoginResponse(
        user=UserProfile.model_validate(user),
        csrf_token=csrf,
        must_change_password=user.must_change_password,
        message=f"Welcome back, {user.full_name.split()[0]}",
    )


@router.post("/refresh", response_model=LoginResponse)
def refresh_session(request: Request, response: Response, db: Db, ctx: Ctx) -> LoginResponse:
    """Rotate the refresh token and mint a new access token."""
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not token:
        raise AuthenticationError("Not authenticated")
    user, access, new_refresh, csrf = auth_service.rotate_session(db, token, ctx)
    set_auth_cookies(response, access, new_refresh, csrf)
    return LoginResponse(
        user=UserProfile.model_validate(user),
        csrf_token=csrf,
        must_change_password=user.must_change_password,
        message="Session refreshed",
    )


@router.post("/logout", response_model=Message)
def logout(request: Request, response: Response, db: Db, ctx: Ctx) -> Message:
    """Revoke the current session. Safe to call when already signed out."""
    token = request.cookies.get(settings.REFRESH_COOKIE_NAME)
    auth_service.revoke_session(db, token)

    access = request.cookies.get(settings.ACCESS_COOKIE_NAME)
    if access:
        from app.core.security import decode_token
        from app.models.user import User

        payload = decode_token(access, "access")
        if payload:
            user = db.get(User, int(payload["sub"]))
            if user:
                record_activity(
                    db, event_type=EventType.LOGOUT, user=user,
                    description="Signed out", context=ctx,
                )
    clear_auth_cookies(response)
    return Message(message="Signed out successfully")


@router.get("/me", response_model=UserProfile)
def me(user: CurrentUser) -> UserProfile:
    return UserProfile.model_validate(user)


@router.put("/me", response_model=UserProfile)
def update_me(payload: ProfileUpdate, user: CurrentUserCsrf, db: Db, ctx: Ctx) -> UserProfile:
    """Self-service profile update. Role, status and Employee ID are not editable here."""
    changes = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "email" in changes:
        from sqlalchemy import func, select

        from app.models.user import User as UserModel

        clash = db.execute(
            select(UserModel.id).where(
                func.lower(UserModel.email) == str(changes["email"]).lower(),
                UserModel.id != user.id,
            )
        ).first()
        if clash:
            raise ValidationError("That email address is already in use.")

    for field, value in changes.items():
        setattr(user, field, str(value) if field == "email" else value)
    db.add(user)
    record_activity(
        db, event_type=EventType.PROFILE_UPDATED, user=user,
        description="Updated their profile", context=ctx,
        metadata={"fields": sorted(changes)},
    )
    return UserProfile.model_validate(user)


@router.post("/change-password", response_model=Message)
def change_password(
    payload: ChangePasswordRequest, request: Request, response: Response,
    user: CurrentUserCsrf, db: Db, ctx: Ctx,
) -> Message:
    """Change your own password. All other sessions are revoked."""
    if payload.new_password != payload.confirm_password:
        raise ValidationError("New password and confirmation do not match.")

    auth_service.change_own_password(db, user, payload.current_password, payload.new_password, ctx)

    # Keep the caller signed in with a brand new session.
    access, refresh, csrf = auth_service.issue_session(db, user, ctx)
    set_auth_cookies(response, access, refresh, csrf)
    return Message(
        message="Password changed successfully",
        detail="You have been signed out of all other devices.",
    )


@router.get("/password-policy", response_model=PasswordPolicyResponse)
def password_policy() -> PasswordPolicyResponse:
    return PasswordPolicyResponse(
        min_length=settings.PASSWORD_MIN_LENGTH, requirements=describe_policy()
    )


@router.post(
    "/forgot-password", response_model=Message, status_code=status.HTTP_202_ACCEPTED
)
def forgot_password(payload: ForgotPasswordRequest, db: Db, ctx: Ctx) -> Message:
    """Record a reset request for administrator action.

    No email transport is configured in this deployment, so the portal
    deliberately does not send a reset link. The request is audited and an
    administrator issues a temporary password from the admin panel. The
    response is identical whether or not the name matches an account.
    """
    resolved = auth_service.get_user_by_username(db, payload.username)
    # Namesakes resolve to a list; for an audit line "somebody asked" is enough.
    user = None if isinstance(resolved, list) else resolved
    record_activity(
        db,
        event_type=EventType.PASSWORD_RESET,
        user=user,
        employee_id=payload.username.strip(),
        description="Password reset requested via the sign-in page",
        success=user is not None,
        context=ctx,
        metadata={"channel": "self_service_request"},
    )
    return Message(
        message="Request received",
        detail=(
            "If that Employee ID exists, an administrator has been notified. "
            "Please contact your portal administrator to receive a temporary password."
        ),
    )
