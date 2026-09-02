"""User schemas.

No schema in this module contains ``password_hash``; the field is never
serialised anywhere in the application.
"""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models.enums import AccountStatus, RoleName
from app.schemas.common import ORMModel


class UserProfile(ORMModel):
    """Returned to the signed-in user about themselves."""

    id: int
    employee_id: str
    full_name: str
    email: EmailStr
    department: str | None = None
    job_title: str | None = None
    role: str = Field(validation_alias="role_name")
    status: str
    is_admin: bool
    must_change_password: bool
    created_at: datetime
    last_login_at: datetime | None = None
    last_activity_at: datetime | None = None
    password_changed_at: datetime | None = None
    login_count: int


class UserAdminView(ORMModel):
    """Richer view, exposed only through admin endpoints."""

    id: int
    employee_id: str
    full_name: str
    email: EmailStr
    department: str | None = None
    job_title: str | None = None
    phone: str | None = None
    role: str = Field(validation_alias="role_name")
    status: str
    is_active: bool
    is_deleted: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
    last_activity_at: datetime | None = None
    login_count: int
    failed_login_attempts: int
    locked_until: datetime | None = None
    password_changed_at: datetime | None = None
    must_change_password: bool
    created_by_id: int | None = None
    notes: str | None = None


class UserCreate(BaseModel):
    """Creating an account needs only a name and an email address.

    The name doubles as the sign-in username. ``employee_id`` stays as the
    internal identifier the audit trail and permissions key on, but the admin
    no longer has to invent one — it is derived from the name when omitted.
    """

    full_name: str = Field(min_length=2, max_length=160)
    employee_id: str | None = Field(
        default=None, max_length=64, examples=["ARWL12345"],
        description="Optional. Generated from the full name when left blank.",
    )
    email: EmailStr
    department: str | None = Field(default=None, max_length=120)
    job_title: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    role: RoleName = RoleName.USER
    temporary_password: str | None = Field(
        default=None,
        max_length=128,
        description="Left blank, a compliant password is generated and returned once.",
    )
    status: AccountStatus = AccountStatus.ACTIVE
    require_password_change: bool = True
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("employee_id")
    @classmethod
    def _clean_employee_id(cls, v: str | None) -> str | None:
        if v is None or not v.strip():
            return None
        v = v.strip().upper()
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Employee ID may only contain letters, numbers, hyphens and underscores")
        if len(v) < 2:
            raise ValueError("Employee ID must be at least 2 characters")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    # Correctable after the fact: the ID is generated at creation, so a
    # placeholder or a typo needs a way out.
    employee_id: str | None = Field(default=None, min_length=2, max_length=64)
    email: EmailStr | None = None
    department: str | None = Field(default=None, max_length=120)
    job_title: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    role: RoleName | None = None
    status: AccountStatus | None = None
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=2000)


    _clean_employee_id = field_validator("employee_id")(
        UserCreate._clean_employee_id.__func__  # type: ignore[attr-defined]
    )


class UserCreatedResponse(BaseModel):
    user: UserAdminView
    temporary_password: str | None = Field(
        default=None,
        description="Shown once at creation time; it is not stored in retrievable form.",
    )


class PasswordResetResponse(BaseModel):
    user_id: int
    employee_id: str
    temporary_password: str
    message: str = "Password reset. Share this temporary password securely."


class ProfileUpdate(BaseModel):
    """Fields a user may change about themselves."""

    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    employee_id: str | None = Field(default=None, min_length=2, max_length=64)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=40)

    _clean_employee_id = field_validator("employee_id")(
        UserCreate._clean_employee_id.__func__  # type: ignore[attr-defined]
    )
