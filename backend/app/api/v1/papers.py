"""Papers API routes — list papers for a survey."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models.user import User
from app.schemas.paper import PaperListResponse, PaperResponse
from app.services.survey_service import SurveyService

router = APIRouter()


@router.get("", response_model=PaperListResponse)
async def list_papers(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get all papers for a survey with their IEEE citations and summaries."""
    service = SurveyService(db)
    papers = await service.get_papers(survey_id, current_user.id)
    return PaperListResponse(
        papers=[PaperResponse.model_validate(p) for p in papers],
        total=len(papers),
    )
