"""
Autonomous Literature Survey – Backend
FastAPI application entry-point.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, Base
from app.api.surveys import router as surveys_router
from app.api.websocket import router as ws_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    log.info("Starting Autonomous Literature Survey API", version="1.0.0")
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    log.info("Shutting down API")
    await engine.dispose()


app = FastAPI(
    title="Autonomous Literature Survey API",
    description="Production-grade Agentic RAG for automated academic literature review.",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(surveys_router, prefix="/api/v1/surveys", tags=["surveys"])
app.include_router(ws_router, prefix="/ws", tags=["websocket"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "ok", "service": "autonomous-literature-survey"}
