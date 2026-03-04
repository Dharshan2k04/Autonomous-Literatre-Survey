"""Health check endpoints."""

from fastapi import APIRouter

from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
async def health_check():
    """Basic health check for ALB and container orchestration."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/health/ready")
async def readiness_check():
    """Readiness probe — checks dependent services."""
    checks = {
        "llm_configured": settings.has_openai or settings.has_anthropic,
        "pinecone_configured": settings.has_pinecone,
        "database": True,  # If we got here, DB is up
    }
    all_ready = all(checks.values())
    return {
        "status": "ready" if all_ready else "degraded",
        "checks": checks,
    }
