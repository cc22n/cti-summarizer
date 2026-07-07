"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1.alerts import router as alerts_router
from app.api.v1.sources import router as sources_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.summaries import router as summaries_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.categories import router as categories_router
from app.api.v1.auth import router as auth_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(alerts_router)
api_v1_router.include_router(sources_router)
api_v1_router.include_router(dashboard_router)
api_v1_router.include_router(summaries_router)
api_v1_router.include_router(predictions_router)
api_v1_router.include_router(categories_router)
