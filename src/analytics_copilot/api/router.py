from fastapi import APIRouter

from analytics_copilot.api.routers import health, query

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(query.router)
