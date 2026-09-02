"""Authentication: login, lockout, refresh-token sessions and password changes."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.core import security
from app.core.config import settings
from app.core.exceptions import (
    AccountLockedError, AuthenticationError, ConflictError, RateLimitError, ValidationError,
)
from app.core.logging_config import get_logger
from app.core.password_policy import PasswordPolicyError, validate_password
from app.database.base import utcnow
from app.models.enums import AccountStatus, EventType
from app.models.user import LoginAttempt, PasswordHistory, Session, User
from app.services.activity_service import record_activity
from app.utils.request_context import RequestContext

logger = get_logger(__name__)

# Returned for every failed login regardless of cause, so the endpoint cannot be
# used to enumerate valid employee IDs.
GENERIC_LOGIN_ERROR = "Invalid name or password"


def _as_utc(value: datetime | None) -> datetime | None:
    """SQLite hands back naive datetimes; normalise before comparing."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _record_attempt(
    db: DbSession,
    employee_id: str,
    *,
    user: User | None,
    successful: bool,
    reason: str | None,
    context: RequestContext | None,
) -> None:
    db.add(
        LoginAttempt(
            employee_id=employee_id[:64],
            user_id=user.id if user else None,
            successful=successful,
            failure_reason=reason,
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
            attempted_at=utcnow(),
        )
    )
    db.flush()


def check_login_rate_limit(
    db: DbSession, employee_id: str, context: RequestContext | None
) -> None:
    """Throttle by employee ID and by source IP over a sliding window."""
    window_start = utcnow() - timedelta(seconds=settings.LOGIN_RATE_LIMIT_WINDOW_SECONDS)

    by_employee = db.execute(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.employee_id == employee_id,
            LoginAttempt.successful.is_(False),
            LoginAttempt.attempted_at >= window_start,
        )
    ).scalar_one()

    by_ip = 0
    if context and context.ip_address:
        by_ip = db.execute(
            select(func.count())
            .select_from(LoginAttempt)
            .where(
                LoginAttempt.ip_address == context.ip_address,
                LoginAttempt.successful.is_(False),
                LoginAttempt.attempted_at >= window_start,
            )
        ).scalar_one()

    limit = settings.LOGIN_RATE_LIMIT_ATTEMPTS
    if by_employee >= limit or by_ip >= limit * 3:
        raise RateLimitError(
            "Too many login attempts. Please wait a few minutes and try again."
        )


def normalise_name(value: str) -> str:
    """Fold a display name to its comparison form: trimmed, single-spaced, lower."""
    return " ".join((value or "").split()).lower()


def get_user_by_username(db: DbSession, username: str) -> User | list[User] | None:
    """Resolve a sign-in name to exactly one account.

    Full names are not unique the way employee IDs are — namesakes are normal —
    so this can legitimately match several rows. When it does, the sign-in-able
    accounts decide it: exactly one means that is the person, and anything else
    is genuinely ambiguous. A list is returned in that case so the caller can
    refuse rather than guess, because guessing would sign somebody into a
    colleague's account.
    """
    wanted = normalise_name(username)
    if not wanted:
        return None

    candidates = [
        user
        for user in db.execute(select(User).where(User.is_deleted.is_(False))).scalars().unique()
        if normalise_name(user.full_name) == wanted
    ]
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    usable = [user for user in candidates if user.can_login]
    return usable[0] if len(usable) == 1 else candidates


def reject_duplicate_name(db: DbSession, full_name: str, *, exclude_id: int | None = None) -> None:
    """Full names are sign-in credentials, so they have to be unique.

    Compared on the same normalised form authentication uses, and scoped to
    accounts that are not deleted — a namesake who has left should not block a
    new joiner. Shared by the admin console and self-service profile editing:
    a user renaming themselves onto a colleague's name would make both of them
    ambiguous and lock them both out.
    """
    wanted = normalise_name(full_name)
    for other in db.execute(select(User).where(User.is_deleted.is_(False))).scalars().unique():
        if other.id != exclude_id and normalise_name(other.full_name) == wanted:
            raise ConflictError(
                f"'{full_name.strip()}' is already the sign-in name for another account. "
                "Names are used to sign in, so they must be unique."
            )


def reject_duplicate_email(db: DbSession, email: str, *, exclude_id: int | None = None) -> None:
    """Live accounts only, matching the partial unique index."""
    clash = db.execute(
        select(User.id).where(
            func.lower(User.email) == str(email).lower(),
            User.id != exclude_id,
            User.is_deleted.is_(False),
        )
    ).first()
    if clash:
        raise ConflictError("That email address is already in use.")


def reject_duplicate_employee_id(
    db: DbSession, employee_id: str, *, exclude_id: int | None = None
) -> None:
    clash = db.execute(
        select(User.id).where(
            func.lower(User.employee_id) == str(employee_id).lower(),
            User.id != exclude_id,
            User.is_deleted.is_(False),
        )
    ).first()
    if clash:
        raise ConflictError(f"Employee ID '{employee_id}' is already in use.")


def get_user_by_employee_id(db: DbSession, employee_id: str) -> User | None:
    return db.execute(
        select(User).where(
            func.lower(User.employee_id) == employee_id.strip().lower(),
            User.is_deleted.is_(False),
        )
    ).scalars().first()


def authenticate(
    db: DbSession,
    username: str,
    password: str,
    context: RequestContext | None = None,
) -> User:
    """Validate credentials or raise. Every outcome is recorded.

    ``username`` is the person's full name. The audit trail and the rate-limit
    bucket key on whatever identifier was submitted, which is what an operator
    reading the log needs to see.
    """
    username = (username or "").strip()
    if not username or not password:
        raise AuthenticationError(GENERIC_LOGIN_ERROR)

    check_login_rate_limit(db, username, context)
    resolved = get_user_by_username(db, username)
    # Several sign-in-able namesakes: there is no safe way to choose one.
    ambiguous = isinstance(resolved, list)
    user = None if ambiguous else resolved

    def fail(reason: str, *, error: Exception | None = None) -> None:
        """Persist the attempt, then raise.

        The commit is essential: the caller's exception handler rolls the
        request transaction back, which would otherwise discard both the audit
        trail and the incremented lockout counter.
        """
        _record_attempt(db, username, user=user, successful=False, reason=reason, context=context)
        record_activity(
            db,
            event_type=EventType.FAILED_LOGIN,
            user=user,
            employee_id=username,
            user_name=user.full_name if user else None,
            description=f"Failed login attempt ({reason})",
            success=False,
            context=context,
            metadata={"reason": reason},
        )
        logger.warning("Failed login for username=%s reason=%s", username, reason)
        db.commit()
        raise error or AuthenticationError(GENERIC_LOGIN_ERROR)

    if user is None:
        # Verify against a real hash so timing does not reveal non-existence.
        security.verify_password(password, security.DUMMY_HASH)
        fail("ambiguous_name" if ambiguous else "unknown_username")

    locked_until = _as_utc(user.locked_until)
    if locked_until and locked_until > utcnow():
        minutes = max(1, int((locked_until - utcnow()).total_seconds() // 60) + 1)
        fail(
            "account_locked",
            error=AccountLockedError(
                f"Account is temporarily locked due to repeated failed logins. "
                f"Try again in about {minutes} minute(s) or contact an administrator."
            ),
        )

    if not user.can_login:
        fail(
            "account_disabled",
            error=AuthenticationError(
                "This account is not active. Please contact your administrator."
            ),
        )

    if not security.verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.MAX_FAILED_LOGIN_ATTEMPTS:
            user.locked_until = utcnow() + timedelta(minutes=settings.ACCOUNT_LOCKOUT_MINUTES)
            user.status = AccountStatus.LOCKED
            db.add(user)
            fail(
                "bad_password_locked",
                error=AccountLockedError(
                    f"Account locked after {settings.MAX_FAILED_LOGIN_ATTEMPTS} failed attempts. "
                    f"Try again in {settings.ACCOUNT_LOCKOUT_MINUTES} minutes."
                ),
            )
        db.add(user)
        fail("bad_password")

    # Success: reset counters and opportunistically upgrade the hash.
    if security.needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)
    user.failed_login_attempts = 0
    user.locked_until = None
    if user.status == AccountStatus.LOCKED:
        user.status = AccountStatus.ACTIVE
    user.last_login_at = utcnow()
    user.last_activity_at = utcnow()
    user.login_count += 1
    db.add(user)

    _record_attempt(db, username, user=user, successful=True, reason=None, context=context)
    record_activity(
        db,
        event_type=EventType.LOGIN,
        user=user,
        description="Signed in to MF AR Workstation",
        context=context,
    )
    return user


def issue_session(
    db: DbSession, user: User, context: RequestContext | None = None
) -> tuple[str, str, str]:
    """Create a refresh session. Returns ``(access, refresh, csrf)`` tokens."""
    access_token, _ = security.create_access_token(user.id, user.role_name, user.employee_id)
    refresh_token, refresh_expiry = security.create_refresh_token(user.id)

    db.add(
        Session(
            user_id=user.id,
            refresh_token_hash=security.hash_refresh_token(refresh_token),
            issued_at=utcnow(),
            expires_at=refresh_expiry,
            last_used_at=utcnow(),
            ip_address=context.ip_address if context else None,
            user_agent=context.user_agent if context else None,
        )
    )
    db.flush()
    return access_token, refresh_token, security.generate_csrf_token()


def rotate_session(
    db: DbSession, refresh_token: str, context: RequestContext | None = None
) -> tuple[User, str, str, str]:
    """Validate a refresh token, revoke it and issue a fresh pair.

    Rotation on every use means a stolen refresh token is usable at most once
    before the legitimate client's next refresh invalidates it.
    """
    payload = security.decode_token(refresh_token, "refresh")
    if not payload:
        raise AuthenticationError("Session expired. Please sign in again.")

    token_hash = security.hash_refresh_token(refresh_token)
    session = db.execute(
        select(Session).where(Session.refresh_token_hash == token_hash)
    ).scalars().first()

    if session is None or session.revoked_at is not None:
        raise AuthenticationError("Session expired. Please sign in again.")
    if (_as_utc(session.expires_at) or utcnow()) <= utcnow():
        raise AuthenticationError("Session expired. Please sign in again.")

    idle_cutoff = utcnow() - timedelta(minutes=settings.SESSION_IDLE_TIMEOUT_MINUTES)
    last_used = _as_utc(session.last_used_at) or _as_utc(session.issued_at)
    if last_used and last_used < idle_cutoff:
        session.revoked_at = utcnow()
        db.add(session)
        raise AuthenticationError("Session timed out due to inactivity. Please sign in again.")

    user = db.get(User, session.user_id)
    if user is None or not user.can_login:
        session.revoked_at = utcnow()
        db.add(session)
        raise AuthenticationError("This account is no longer active.")

    session.revoked_at = utcnow()
    session.last_used_at = utcnow()
    db.add(session)

    access, new_refresh, csrf = issue_session(db, user, context)
    user.last_activity_at = utcnow()
    db.add(user)
    return user, access, new_refresh, csrf


def revoke_session(db: DbSession, refresh_token: str | None) -> None:
    if not refresh_token:
        return
    token_hash = security.hash_refresh_token(refresh_token)
    session = db.execute(
        select(Session).where(Session.refresh_token_hash == token_hash)
    ).scalars().first()
    if session and session.revoked_at is None:
        session.revoked_at = utcnow()
        db.add(session)


def revoke_all_sessions(db: DbSession, user_id: int, *, except_hash: str | None = None) -> int:
    """Used after a password change, account disable or admin reset."""
    sessions = db.execute(
        select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
    ).scalars().all()
    count = 0
    for session in sessions:
        if except_hash and session.refresh_token_hash == except_hash:
            continue
        session.revoked_at = utcnow()
        db.add(session)
        count += 1
    return count


def _assert_not_reused(db: DbSession, user: User, new_password: str) -> None:
    recent = db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(settings.PASSWORD_HISTORY_DEPTH)
    ).scalars().all()
    for entry in recent:
        if security.verify_password(new_password, entry.password_hash):
            raise ValidationError(
                f"You cannot reuse any of your last {settings.PASSWORD_HISTORY_DEPTH} passwords."
            )


def set_password(
    db: DbSession,
    user: User,
    new_password: str,
    *,
    changed_by: User | None = None,
    enforce_history: bool = True,
    must_change: bool = False,
) -> None:
    """Validate, hash and store a new password, recording it in history."""
    try:
        validate_password(new_password, employee_id=user.employee_id, full_name=user.full_name)
    except PasswordPolicyError as exc:
        raise ValidationError("Password does not meet the security requirements", details=exc.errors)

    if enforce_history:
        _assert_not_reused(db, user, new_password)
        if security.verify_password(new_password, user.password_hash):
            raise ValidationError("Your new password must be different from your current password.")

    db.add(
        PasswordHistory(
            user_id=user.id,
            password_hash=user.password_hash,
            created_at=utcnow(),
            changed_by_id=changed_by.id if changed_by else None,
        )
    )
    user.password_hash = security.hash_password(new_password)
    user.password_changed_at = utcnow()
    user.must_change_password = must_change
    if user.status == AccountStatus.PENDING_PASSWORD_CHANGE and not must_change:
        user.status = AccountStatus.ACTIVE
    db.add(user)
    db.flush()

    # Trim history so it does not grow unbounded.
    stale = db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .offset(settings.PASSWORD_HISTORY_DEPTH)
    ).scalars().all()
    for entry in stale:
        db.delete(entry)


def change_own_password(
    db: DbSession,
    user: User,
    current_password: str,
    new_password: str,
    context: RequestContext | None = None,
) -> None:
    if not security.verify_password(current_password, user.password_hash):
        record_activity(
            db,
            event_type=EventType.PASSWORD_CHANGED,
            user=user,
            description="Password change failed (incorrect current password)",
            success=False,
            context=context,
            commit=True,
        )
        raise AuthenticationError("Your current password is incorrect.")

    set_password(db, user, new_password, changed_by=user)
    revoke_all_sessions(db, user.id)
    record_activity(
        db,
        event_type=EventType.PASSWORD_CHANGED,
        user=user,
        description="Password changed successfully",
        context=context,
    )
