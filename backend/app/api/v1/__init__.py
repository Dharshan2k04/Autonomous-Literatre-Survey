"""API v1 router — aggregates all route modules."""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.surveys import router as surveys_router
from app.api.v1.papers import router as papers_router
from app.api.v1.chat import router as chat_router
from app.api.v1.health import router as health_router

router = APIRouter(prefix="/api/v1")

router.include_router(health_router, tags=["health"])
router.include_router(auth_router, prefix="/auth", tags=["auth"])
router.include_router(surveys_router, prefix="/surveys", tags=["surveys"])
router.include_router(papers_router, prefix="/surveys/{survey_id}/papers", tags=["papers"])
router.include_router(chat_router, prefix="/surveys/{survey_id}/chat", tags=["chat"])
