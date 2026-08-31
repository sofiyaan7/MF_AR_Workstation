"""Extracts client metadata (IP, browser, OS, device) from a request."""
from dataclasses import dataclass

from fastapi import Request
from user_agents import parse as parse_user_agent

from app.core.config import settings


@dataclass(frozen=True)
class RequestContext:
    ip_address: str | None
    user_agent: str | None
    browser: str | None
    os: str | None
    device: str | None


def _client_ip(request: Request) -> str | None:
    """Resolve the client IP.

    Proxy headers are only honoured outside production-behind-nothing setups;
    when deployed, the reverse proxy is responsible for setting them correctly.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()[:64]
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()[:64]
    if request.client:
        return request.client.host[:64]
    return None


def get_request_context(request: Request) -> RequestContext:
    raw_ua = (request.headers.get("user-agent") or "")[:512]
    browser = os_name = device = None
    if raw_ua:
        try:
            ua = parse_user_agent(raw_ua)
            browser = f"{ua.browser.family} {ua.browser.version_string}".strip()[:80]
            os_name = f"{ua.os.family} {ua.os.version_string}".strip()[:80]
            if ua.is_mobile:
                device = "Mobile"
            elif ua.is_tablet:
                device = "Tablet"
            elif ua.is_bot:
                device = "Bot"
            else:
                device = "Desktop"
        except Exception:  # pragma: no cover - never fail a request over UA parsing
            pass
    return RequestContext(
        ip_address=_client_ip(request),
        user_agent=raw_ua or None,
        browser=browser,
        os=os_name,
        device=device,
    )


def set_auth_cookies(
    response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
) -> None:
    """Access + refresh are HttpOnly; the CSRF token is readable by the SPA."""
    common = {
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "domain": settings.COOKIE_DOMAIN,
        "path": "/",
    }
    response.set_cookie(
        settings.ACCESS_COOKIE_NAME,
        access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **common,
    )
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        **common,
    )
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf_token,
        httponly=False,  # the SPA must echo this back in a header
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        **common,
    )


def clear_auth_cookies(response) -> None:
    for name in (
        settings.ACCESS_COOKIE_NAME,
        settings.REFRESH_COOKIE_NAME,
        settings.CSRF_COOKIE_NAME,
    ):
        response.delete_cookie(name, path="/", domain=settings.COOKIE_DOMAIN)
