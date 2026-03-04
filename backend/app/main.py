"""FastAPI application factory — the main entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.v1 import router as v1_router
from app.config import get_settings
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.core.logging import setup_logging
from app.websocket.chat import websocket_endpoint

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    setup_logging()

    from app.core.logging import get_logger
    logger = get_logger("app.startup")
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        llm_provider=settings.LLM_PROVIDER,
        has_openai=settings.has_openai,
        has_anthropic=settings.has_anthropic,
        has_pinecone=settings.has_pinecone,
    )

    yield

    logger.info("application_shutting_down")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Autonomous Literature Survey API",
        description="Production-grade Agentic RAG for automated academic literature review",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ---- Middleware ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Session middleware for OAuth
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
    )

    # ---- Exception handlers ----
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ---- Routes ----
    app.include_router(v1_router)

    # ---- WebSocket ----
    @app.websocket("/ws/surveys/{survey_id}")
    async def ws_survey(websocket, survey_id: str):
        await websocket_endpoint(websocket, survey_id)

    return app


# Application instance
app = create_app()
