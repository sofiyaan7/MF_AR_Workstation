"""Aggregates every route module under the API prefix."""
from fastapi import APIRouter

from app.api.routes import activity, admin_activity, admin_projects, admin_users, auth, projects

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(activity.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_projects.router)
api_router.include_router(admin_activity.router)
