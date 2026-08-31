"""Password complexity rules, shared by self-service change and admin creation."""
import re

from app.core.config import settings

SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>/?~`"

# Rejected outright regardless of complexity.
_COMMON_PASSWORDS = {
    "password", "password1", "password123", "welcome1", "welcome123",
    "admin123", "qwerty123", "letmein123", "changeme123", "administrator",
}


class PasswordPolicyError(ValueError):
    """Raised with a human-readable list of unmet requirements."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


def describe_policy() -> list[str]:
    return [
        f"At least {settings.PASSWORD_MIN_LENGTH} characters",
        "At least one uppercase letter (A-Z)",
        "At least one lowercase letter (a-z)",
        "At least one number (0-9)",
        "At least one special character",
        "Must not repeat one of your recent passwords",
    ]


def validate_password(password: str, *, employee_id: str = "", full_name: str = "") -> None:
    """Raise :class:`PasswordPolicyError` if ``password`` fails any rule."""
    errors: list[str] = []

    if len(password) < settings.PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters long")
    if len(password) > 128:
        errors.append("Password must be at most 128 characters long")
    if not re.search(r"[A-Z]", password):
        errors.append("Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("Password must contain a lowercase letter")
    if not re.search(r"[0-9]", password):
        errors.append("Password must contain a number")
    if not re.search(f"[{re.escape(SPECIAL_CHARS)}]", password):
        errors.append("Password must contain a special character")
    if password.lower() in _COMMON_PASSWORDS:
        errors.append("Password is too common")
    if employee_id and employee_id.lower() in password.lower():
        errors.append("Password must not contain your Employee ID")
    for part in (full_name or "").split():
        if len(part) > 2 and part.lower() in password.lower():
            errors.append("Password must not contain your name")
            break

    if errors:
        raise PasswordPolicyError(errors)
