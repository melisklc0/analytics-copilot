from fastapi import APIRouter

from analytics_copilot.api.routers import document, health, query

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(document.router)
api_router.include_router(query.router)
