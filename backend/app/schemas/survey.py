"""Survey schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.survey import SurveyStatus


# ---- Request schemas ----

class SurveyCreate(BaseModel):
    topic: str = Field(..., min_length=5, max_length=1000, description="Research topic to survey")


class SurveyChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


# ---- Response schemas ----

class SurveyResponse(BaseModel):
    id: UUID
    topic: str
    status: SurveyStatus
    progress: int
    paper_count: int
    expanded_queries: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class SurveyDetailResponse(SurveyResponse):
    survey_markdown: str | None = None
    bibliography: dict | None = None
    taxonomy: dict | None = None


class SurveyListResponse(BaseModel):
    surveys: list[SurveyResponse]
    total: int


class SurveyProgressEvent(BaseModel):
    """WebSocket event for real-time progress updates."""
    survey_id: str
    status: SurveyStatus
    progress: int
    message: str
    data: dict | None = None


class ChatResponse(BaseModel):
    answer: str
    cited_papers: list[dict] = []
    sources: list[str] = []
