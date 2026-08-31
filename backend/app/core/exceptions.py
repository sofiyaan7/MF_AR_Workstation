"""Domain exceptions mapped to HTTP responses in app/main.py."""


class AppError(Exception):
    status_code = 400
    code = "app_error"

    def __init__(self, message: str, *, details: list[str] | None = None) -> None:
        self.message = message
        self.details = details or []
        super().__init__(message)


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_failed"


class AccountLockedError(AppError):
    status_code = 423
    code = "account_locked"


class RateLimitError(AppError):
    status_code = 429
    code = "rate_limited"


class PermissionDeniedError(AppError):
    status_code = 403
    code = "permission_denied"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"
