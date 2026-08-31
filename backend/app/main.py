"""MF AR Workstation — application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging_config import configure_logging, get_logger
from app.core.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "Starting %s (environment=%s, api_prefix=%s)",
        settings.APP_NAME, settings.ENVIRONMENT, settings.API_PREFIX,
    )
    yield
    logger.info("Shutting down %s", settings.APP_NAME)


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description=(
        "Internal project portal: authentication, project catalogue, "
        "role-based administration and audit logging."
    ),
    version="1.0.0",
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,  # required for the auth cookies
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", settings.CSRF_HEADER_NAME],
    expose_headers=["X-Request-ID"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.code, "message": exc.message, "details": exc.details},
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Flatten Pydantic errors into readable messages without echoing input values."""
    details = []
    for err in exc.errors():
        location = ".".join(str(p) for p in err["loc"] if p not in ("body", "query", "path"))
        details.append(f"{location}: {err['msg']}" if location else err["msg"])
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Please correct the highlighted fields.",
            "details": details,
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "http_error",
            "message": exc.detail if isinstance(exc.detail, str) else "Request failed",
            "details": [],
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never leak a stack trace or internal message to the client."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "Something went wrong. Please try again or contact support.",
            "details": [],
        },
    )


@app.get("/health", tags=["System"])
def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME, "environment": settings.ENVIRONMENT}


@app.get(f"{settings.API_PREFIX}/health", tags=["System"])
def api_health() -> dict:
    from sqlalchemy import text

    from app.database.session import engine

    database = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - depends on deployment
        logger.error("Database health check failed: %s", type(exc).__name__)
        database = "unavailable"
    return {"status": "ok" if database == "ok" else "degraded", "database": database}


app.include_router(api_router, prefix=settings.API_PREFIX)
