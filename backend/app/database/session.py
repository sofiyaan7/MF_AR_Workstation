"""Engine and session factory."""
import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings

connect_args: dict = {}
engine_kwargs: dict = {"pool_pre_ping": True, "echo": settings.SQL_ECHO, "future": True}

if settings.DATABASE_URL.startswith("sqlite"):
    # Only used by the test suite; Postgres is the production target.
    connect_args = {"check_same_thread": False}
    engine_kwargs.pop("pool_pre_ping")
elif os.environ.get("VERCEL"):
    # Serverless: a function sandbox handles one request at a time and may be
    # frozen or discarded straight after, so an in-process pool only holds
    # connections nobody can reuse and exhausts the Postgres connection limit
    # once requests fan out. Pooling is delegated to the managed pooler that
    # DATABASE_URL must point at (e.g. Neon/Supabase pgbouncer).
    engine_kwargs["poolclass"] = NullPool

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, **engine_kwargs)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
