"""Vercel serverless entrypoint for the FastAPI backend.

Vercel treats every file under ``api/`` as a function. The ASGI app exported
here is served for all ``/api/*`` requests via the rewrite in vercel.json,
which keeps the API on the same origin as the SPA so the HttpOnly auth
cookies continue to work without any CORS relaxation.

The backend package lives in ``backend/``, which is not on sys.path in the
function sandbox, so it is added before importing the app. ``backend/app/**``
is force-included in the bundle by the ``includeFiles`` setting.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.main import app  # noqa: E402  (path setup must run first)

# Vercel's Python runtime detects and serves this ASGI callable.
__all__ = ["app"]
