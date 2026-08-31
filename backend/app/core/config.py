"""Application configuration, loaded exclusively from the environment."""
from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- Application ------------------------------------------------------
    APP_NAME: str = "MF AR Workstation"
    ENVIRONMENT: str = "development"
    API_PREFIX: str = "/api"
    LOG_LEVEL: str = "INFO"

    # --- Database ---------------------------------------------------------
    DATABASE_URL: str = "postgresql+psycopg2://portal:portal@localhost:5432/mf_ar_workstation"
    SQL_ECHO: bool = False

    # --- Security ---------------------------------------------------------
    SECRET_KEY: str = Field(default="dev-only-insecure-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    SESSION_IDLE_TIMEOUT_MINUTES: int = 480

    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str | None = None
    ACCESS_COOKIE_NAME: str = "mfar_access"
    REFRESH_COOKIE_NAME: str = "mfar_refresh"
    CSRF_COOKIE_NAME: str = "mfar_csrf"
    CSRF_HEADER_NAME: str = "X-CSRF-Token"

    # --- Brute force / lockout -------------------------------------------
    MAX_FAILED_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCKOUT_MINUTES: int = 15
    LOGIN_RATE_LIMIT_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300

    # --- Password policy --------------------------------------------------
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_HISTORY_DEPTH: int = 5

    # --- CORS -------------------------------------------------------------
    FRONTEND_URL: str = "http://localhost:5173"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # --- Bootstrap admin (first-run only) ---------------------------------
    FIRST_ADMIN_EMPLOYEE_ID: str = "ADMIN001"
    FIRST_ADMIN_NAME: str = "System Administrator"
    FIRST_ADMIN_EMAIL: str = "admin@example.com"
    FIRST_ADMIN_PASSWORD: str | None = None

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def _validate_samesite(cls, v: str) -> str:
        v = v.lower()
        if v not in {"lax", "strict", "none"}:
            raise ValueError("COOKIE_SAMESITE must be lax, strict or none")
        return v

    @property
    def cors_origin_list(self) -> List[str]:
        origins = {o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()}
        if self.FRONTEND_URL:
            origins.add(self.FRONTEND_URL.strip())
        return sorted(origins)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production and settings.SECRET_KEY.startswith("dev-only"):
        raise RuntimeError(
            "SECRET_KEY must be set to a strong random value in production. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
        )
    return settings


settings = get_settings()
