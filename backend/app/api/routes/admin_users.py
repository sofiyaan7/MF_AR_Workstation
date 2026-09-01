"""Administrator user management. Every route requires an ADMIN role."""
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, or_, select

from app.auth.dependencies import AdminUser, Ctx, Db
from app.core import security
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.database.base import utcnow
from app.models.enums import AccountStatus, EventType, RoleName
from app.models.user import LoginAttempt, Role, User
from app.schemas.activity import ActivityEntry, LoginHistoryEntry
from app.schemas.common import Message, Page
from app.schemas.user import (
    PasswordResetResponse, UserAdminView, UserCreate, UserCreatedResponse, UserUpdate,
)
from app.services import activity_service, auth_service
from app.services.activity_service import record_activity

router = APIRouter(prefix="/admin/users", tags=["Admin - Users"])


def _reject_duplicate_name(db, full_name: str, *, exclude_id: int | None = None) -> None:
    """Full names are sign-in credentials now, so they have to be unique.

    Compared on the same normalised form authentication uses, and scoped to
    accounts that are not deleted — a namesake who has left should not block a
    new joiner.
    """
    wanted = auth_service.normalise_name(full_name)
    for other in db.execute(select(User).where(User.is_deleted.is_(False))).scalars().unique():
        if other.id != exclude_id and auth_service.normalise_name(other.full_name) == wanted:
            raise ConflictError(
                f"'{full_name.strip()}' is already the sign-in name for another account. "
                "Names are used to sign in, so they must be unique."
            )


def _get_role(db, name: str) -> Role:
    role = db.execute(select(Role).where(Role.name == str(name))).scalars().first()
    if role is None:
        raise NotFoundError(f"Role '{name}' does not exist")
    return role


def _get_user(db, user_id: int, *, include_deleted: bool = False) -> User:
    user = db.get(User, user_id)
    if user is None or (user.is_deleted and not include_deleted):
        raise NotFoundError("User not found")
    return user


def _guard_target(actor: User, target: User, action: str) -> None:
    """Prevent privilege inversion and self-lockout.

    A plain ADMIN may not modify a SUPER_ADMIN, and nobody may disable or
    delete their own account.
    """
    if target.id == actor.id and action in {"disable", "delete", "role"}:
        raise PermissionDeniedError(f"You cannot {action} your own account.")
    if target.is_super_admin and not actor.is_super_admin:
        raise PermissionDeniedError(
            "Only a super administrator can modify a super administrator account."
        )


@router.get("", response_model=Page[UserAdminView])
def list_users(
    admin: AdminUser,
    db: Db,
    search: Annotated[str | None, Query(max_length=160)] = None,
    department: Annotated[str | None, Query(max_length=120)] = None,
    role: Annotated[str | None, Query(max_length=32)] = None,
    status: Annotated[str | None, Query(max_length=32)] = None,
    is_active: bool | None = None,
    include_deleted: bool = False,
    sort: Annotated[str, Query(pattern="^(name|employee_id|last_login|created|logins)$")] = "name",
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[UserAdminView]:
    stmt = select(User)
    if not include_deleted:
        stmt = stmt.where(User.is_deleted.is_(False))
    if search:
        pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(pattern),
                User.employee_id.ilike(pattern),
                User.email.ilike(pattern),
                User.department.ilike(pattern),
            )
        )
    if department:
        stmt = stmt.where(func.lower(User.department) == department.strip().lower())
    if role:
        stmt = stmt.where(User.role.has(Role.name == role.upper()))
    if status:
        stmt = stmt.where(User.status == status.upper())
    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))

    order = {
        "name": (User.full_name.asc(),),
        "employee_id": (User.employee_id.asc(),),
        "last_login": (User.last_login_at.desc().nullslast(),),
        "created": (User.created_at.desc(),),
        "logins": (User.login_count.desc(),),
    }[sort]

    total = db.execute(
        select(func.count()).select_from(stmt.subquery())
    ).scalar_one()
    rows = db.execute(stmt.order_by(*order).limit(limit).offset(offset)).scalars().unique().all()
    return Page(
        items=[UserAdminView.model_validate(u) for u in rows],
        total=total, limit=limit, offset=offset,
    )


@router.get("/departments", response_model=list[str])
def departments(admin: AdminUser, db: Db) -> list[str]:
    rows = db.execute(
        select(User.department)
        .where(User.department.isnot(None), User.is_deleted.is_(False))
        .distinct()
    ).all()
    return sorted({r[0] for r in rows if r[0]})


@router.post("", response_model=UserCreatedResponse, status_code=201)
def create_user(payload: UserCreate, admin: AdminUser, db: Db, ctx: Ctx) -> UserCreatedResponse:
    """Create an employee account. Only listed employees can ever sign in."""
    if payload.role == RoleName.SUPER_ADMIN and not admin.is_super_admin:
        raise PermissionDeniedError("Only a super administrator can create super administrators.")

    existing = db.execute(
        select(User).where(func.lower(User.employee_id) == payload.employee_id.lower())
    ).scalars().first()
    if existing:
        raise ConflictError(f"Employee ID '{payload.employee_id}' is already registered")
    if db.execute(
        select(User.id).where(func.lower(User.email) == payload.email.lower())
    ).first():
        raise ConflictError(f"Email '{payload.email}' is already registered")
    _reject_duplicate_name(db, payload.full_name)

    temp_password = payload.temporary_password or security.generate_temp_password()
    role = _get_role(db, payload.role)

    user = User(
        employee_id=payload.employee_id,
        full_name=payload.full_name.strip(),
        email=str(payload.email).lower(),
        department=(payload.department or "").strip() or None,
        job_title=(payload.job_title or "").strip() or None,
        phone=(payload.phone or "").strip() or None,
        role_id=role.id,
        password_hash="!",  # replaced by set_password below
        status=str(payload.status),
        is_active=payload.status == AccountStatus.ACTIVE,
        created_by_id=admin.id,
        notes=payload.notes,
    )
    db.add(user)
    db.flush()

    # Validates complexity and records the initial history entry.
    auth_service.set_password(
        db, user, temp_password, changed_by=admin, enforce_history=False,
        must_change=payload.require_password_change,
    )
    if payload.require_password_change:
        user.status = str(AccountStatus.PENDING_PASSWORD_CHANGE)
        user.is_active = True

    record_activity(
        db, event_type=EventType.USER_CREATED, user=admin,
        description=f"Created user {user.employee_id} ({user.full_name})",
        target_user_id=user.id, context=ctx,
        metadata={"employee_id": user.employee_id, "role": role.name},
    )
    db.flush()
    db.refresh(user)
    return UserCreatedResponse(
        user=UserAdminView.model_validate(user),
        temporary_password=temp_password if not payload.temporary_password else None,
    )


@router.get("/{user_id}", response_model=UserAdminView)
def get_user(user_id: int, admin: AdminUser, db: Db) -> UserAdminView:
    return UserAdminView.model_validate(_get_user(db, user_id, include_deleted=True))


@router.put("/{user_id}", response_model=UserAdminView)
def update_user(
    user_id: int, payload: UserUpdate, admin: AdminUser, db: Db, ctx: Ctx
) -> UserAdminView:
    user = _get_user(db, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return UserAdminView.model_validate(user)

    if "role" in changes and changes["role"] is not None:
        _guard_target(admin, user, "role")
        if changes["role"] == RoleName.SUPER_ADMIN and not admin.is_super_admin:
            raise PermissionDeniedError("Only a super administrator can grant that role.")
    if {"status", "is_active"} & set(changes):
        _guard_target(admin, user, "disable")
    else:
        _guard_target(admin, user, "update")

    if "full_name" in changes and changes["full_name"]:
        _reject_duplicate_name(db, changes["full_name"], exclude_id=user.id)
    if "email" in changes and changes["email"]:
        clash = db.execute(
            select(User.id).where(
                func.lower(User.email) == str(changes["email"]).lower(), User.id != user.id
            )
        ).first()
        if clash:
            raise ConflictError("That email address is already in use.")

    previous_role = user.role_name
    audit: dict[str, object] = {}

    for field, value in changes.items():
        if value is None and field in {"role", "status", "is_active"}:
            continue
        if field == "role":
            user.role_id = _get_role(db, value).id
            audit["role"] = f"{previous_role} -> {value}"
        elif field == "status":
            user.status = str(value)
            user.is_active = value == AccountStatus.ACTIVE
            audit["status"] = str(value)
            if value != AccountStatus.ACTIVE:
                auth_service.revoke_all_sessions(db, user.id)
        elif field == "is_active":
            user.is_active = bool(value)
            audit["is_active"] = bool(value)
            if not value:
                user.status = str(AccountStatus.DISABLED)
                auth_service.revoke_all_sessions(db, user.id)
            elif user.status == AccountStatus.DISABLED:
                user.status = str(AccountStatus.ACTIVE)
        elif field == "email":
            user.email = str(value).lower()
            audit["email"] = user.email
        else:
            setattr(user, field, value)
            audit[field] = value
    db.add(user)

    event = EventType.USER_UPDATED
    if audit.get("is_active") is False or audit.get("status") in {
        str(AccountStatus.DISABLED), str(AccountStatus.LOCKED)
    }:
        event = EventType.USER_DISABLED
    elif audit.get("is_active") is True or audit.get("status") == str(AccountStatus.ACTIVE):
        event = EventType.USER_ENABLED
    if "role" in audit:
        record_activity(
            db, event_type=EventType.ROLE_CHANGED, user=admin,
            description=f"Changed role for {user.employee_id}: {audit['role']}",
            target_user_id=user.id, context=ctx, metadata={"change": audit["role"]},
        )

    record_activity(
        db, event_type=event, user=admin,
        description=f"Updated user {user.employee_id} ({', '.join(sorted(audit)) or 'no changes'})",
        target_user_id=user.id, context=ctx, metadata=audit,
    )
    db.flush()
    db.refresh(user)
    return UserAdminView.model_validate(user)


@router.post("/{user_id}/enable", response_model=Message)
def enable_user(user_id: int, admin: AdminUser, db: Db, ctx: Ctx) -> Message:
    user = _get_user(db, user_id)
    _guard_target(admin, user, "enable")
    user.is_active = True
    user.status = str(
        AccountStatus.PENDING_PASSWORD_CHANGE if user.must_change_password else AccountStatus.ACTIVE
    )
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    record_activity(
        db, event_type=EventType.USER_ENABLED, user=admin,
        description=f"Enabled user {user.employee_id}", target_user_id=user.id, context=ctx,
    )
    return Message(message=f"{user.full_name} can now sign in")


@router.post("/{user_id}/disable", response_model=Message)
def disable_user(user_id: int, admin: AdminUser, db: Db, ctx: Ctx) -> Message:
    user = _get_user(db, user_id)
    _guard_target(admin, user, "disable")
    user.is_active = False
    user.status = str(AccountStatus.DISABLED)
    revoked = auth_service.revoke_all_sessions(db, user.id)
    db.add(user)
    record_activity(
        db, event_type=EventType.USER_DISABLED, user=admin,
        description=f"Disabled user {user.employee_id}", target_user_id=user.id,
        context=ctx, metadata={"sessions_revoked": revoked},
    )
    return Message(message=f"{user.full_name} has been disabled")


@router.post("/{user_id}/unlock", response_model=Message)
def unlock_user(user_id: int, admin: AdminUser, db: Db, ctx: Ctx) -> Message:
    user = _get_user(db, user_id)
    user.failed_login_attempts = 0
    user.locked_until = None
    if user.status == AccountStatus.LOCKED:
        user.status = str(AccountStatus.ACTIVE)
    db.add(user)
    record_activity(
        db, event_type=EventType.USER_UPDATED, user=admin,
        description=f"Unlocked account {user.employee_id}", target_user_id=user.id, context=ctx,
    )
    return Message(message=f"{user.full_name}'s account has been unlocked")


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
def reset_password(user_id: int, admin: AdminUser, db: Db, ctx: Ctx) -> PasswordResetResponse:
    """Issue a one-time temporary password; the user must change it at next sign-in."""
    user = _get_user(db, user_id)
    _guard_target(admin, user, "reset the password of")

    temp_password = security.generate_temp_password()
    auth_service.set_password(
        db, user, temp_password, changed_by=admin, enforce_history=False, must_change=True
    )
    user.status = str(AccountStatus.PENDING_PASSWORD_CHANGE)
    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    auth_service.revoke_all_sessions(db, user.id)

    record_activity(
        db, event_type=EventType.PASSWORD_RESET, user=admin,
        description=f"Reset password for {user.employee_id}",
        target_user_id=user.id, context=ctx,
    )
    return PasswordResetResponse(
        user_id=user.id, employee_id=user.employee_id, temporary_password=temp_password
    )


@router.delete("/{user_id}", response_model=Message)
def delete_user(user_id: int, admin: AdminUser, db: Db, ctx: Ctx) -> Message:
    """Soft delete. The account stops working; audit history is preserved."""
    user = _get_user(db, user_id)
    _guard_target(admin, user, "delete")

    user.is_deleted = True
    user.is_active = False
    user.deleted_at = utcnow()
    user.status = str(AccountStatus.DISABLED)
    auth_service.revoke_all_sessions(db, user.id)
    db.add(user)
    record_activity(
        db, event_type=EventType.USER_DELETED, user=admin,
        description=f"Deleted user {user.employee_id} ({user.full_name})",
        target_user_id=user.id, context=ctx,
        metadata={"soft_delete": True, "employee_id": user.employee_id},
    )
    return Message(
        message=f"{user.full_name} has been removed",
        detail="Their activity history remains available in the audit log.",
    )


@router.get("/{user_id}/activity", response_model=Page[ActivityEntry])
def user_activity(
    user_id: int, admin: AdminUser, db: Db,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[ActivityEntry]:
    user = _get_user(db, user_id, include_deleted=True)
    rows, total = activity_service.query_activity(
        db, user_id=user.id, limit=limit, offset=offset
    )
    return Page(
        items=[ActivityEntry.model_validate(r) for r in rows],
        total=total, limit=limit, offset=offset,
    )


@router.get("/{user_id}/login-history", response_model=Page[LoginHistoryEntry])
def login_history(
    user_id: int, admin: AdminUser, db: Db,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[LoginHistoryEntry]:
    user = _get_user(db, user_id, include_deleted=True)
    stmt = select(LoginAttempt).where(
        or_(
            LoginAttempt.user_id == user.id,
            func.lower(LoginAttempt.employee_id) == user.employee_id.lower(),
        )
    )
    total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
    rows = db.execute(
        stmt.order_by(LoginAttempt.attempted_at.desc()).limit(limit).offset(offset)
    ).scalars().all()
    return Page(
        items=[LoginHistoryEntry.model_validate(r) for r in rows],
        total=total, limit=limit, offset=offset,
    )
