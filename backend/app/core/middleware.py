"""Security headers and request logging."""
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger("app.request")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Baseline hardening headers on every response.

    The CSP is intentionally strict for the API; the SPA is served separately
    by nginx, which applies its own policy (see frontend/nginx.conf).
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-XSS-Protection"] = "0"  # superseded by CSP
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        response.headers["Cache-Control"] = "no-store"
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Technical request log. Bodies are never logged, so credentials cannot leak."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logger.exception(
                "rid=%s %s %s -> unhandled exception", request_id, request.method,
                request.url.path,
            )
            raise
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-ID"] = request_id
        log = logger.warning if response.status_code >= 400 else logger.info
        log(
            "rid=%s %s %s -> %s (%.1fms)",
            request_id, request.method, request.url.path, response.status_code, duration_ms,
        )
        return response
