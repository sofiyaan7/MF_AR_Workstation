"""Password hashing, token minting and CSRF token helpers.

Nothing in this module logs or returns a secret value.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error
from argon2.low_level import Type
from jose import JWTError, jwt

from app.core.config import settings

# Argon2id with OWASP-recommended parameters for an interactive login flow.
_hasher = PasswordHasher(
    time_cost=3,
    memory_cost=64 * 1024,  # 64 MiB
    parallelism=4,
    hash_len=32,
    salt_len=16,
    type=Type.ID,
)

TokenType = Literal["access", "refresh"]


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password, returning False rather than raising on any failure.

    ``Argon2Error`` covers both a mismatch and a malformed/foreign hash string.
    """
    try:
        _hasher.verify(password_hash, password)
        return True
    except (Argon2Error, ValueError, TypeError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except (Argon2Error, ValueError):
        return True


# Verified against this when the Employee ID is unknown, so that a failed login
# costs the same wall-clock time whether or not the account exists.
DUMMY_HASH = _hasher.hash("timing-equalisation-placeholder")


def create_token(
    subject: str | int,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    """Return ``(encoded_jwt, expiry)``. ``jti`` makes every token unique."""
    now = datetime.now(timezone.utc)
    expire = now + expires_delta
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_urlsafe(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded, expire


def create_access_token(user_id: int, role: str, employee_id: str) -> tuple[str, datetime]:
    return create_token(
        user_id,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        {"role": role, "eid": employee_id},
    )


def create_refresh_token(user_id: int) -> tuple[str, datetime]:
    return create_token(user_id, "refresh", timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS))


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any] | None:
    """Decode and validate a JWT. Returns ``None`` for anything untrustworthy."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
    if expected_type and payload.get("type") != expected_type:
        return None
    if not payload.get("sub"):
        return None
    return payload


def hash_refresh_token(token: str) -> str:
    """Refresh tokens are stored only as a digest, so a DB leak cannot replay them."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def csrf_tokens_match(cookie_token: str | None, header_token: str | None) -> bool:
    if not cookie_token or not header_token:
        return False
    return hmac.compare_digest(cookie_token, header_token)


def generate_temp_password(length: int = 16) -> str:
    """Generate a compliant random password for admin-issued resets."""
    import string

    alphabet = string.ascii_letters + string.digits + "!@#$%^&*-_=+"
    while True:
        candidate = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in candidate)
            and any(c.isupper() for c in candidate)
            and any(c.isdigit() for c in candidate)
            and any(c in "!@#$%^&*-_=+" for c in candidate)
        ):
            return candidate
