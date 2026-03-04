"""Survey API routes — create, list, get, delete surveys."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.agents.graph import SurveyWorkflow
from app.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.schemas.survey import (
    SurveyCreate,
    SurveyDetailResponse,
    SurveyListResponse,
    SurveyResponse,
)
from app.services.survey_service import SurveyService

router = APIRouter()


@router.post("", response_model=SurveyResponse, status_code=201)
async def create_survey(
    body: SurveyCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a new literature survey and start the agent pipeline."""
    service = SurveyService(db)
    survey = await service.create_survey(current_user.id, body.topic)
    survey_id = str(survey.id)
    user_id = str(current_user.id)

    # Run the agent workflow in the background
    async def run_workflow():
        async with AsyncSessionLocal() as session:
            workflow = SurveyWorkflow(session)
            await workflow.run(survey_id, body.topic, user_id)
            await session.commit()

    background_tasks.add_task(run_workflow)

    return SurveyResponse.model_validate(survey)


@router.get("", response_model=SurveyListResponse)
async def list_surveys(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all surveys for the current user."""
    service = SurveyService(db)
    surveys, total = await service.list_surveys(current_user.id, skip=skip, limit=limit)
    return SurveyListResponse(
        surveys=[SurveyResponse.model_validate(s) for s in surveys],
        total=total,
    )


@router.get("/{survey_id}", response_model=SurveyDetailResponse)
async def get_survey(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a survey with full details including markdown and taxonomy."""
    service = SurveyService(db)
    survey = await service.get_survey(survey_id, current_user.id)
    return SurveyDetailResponse.model_validate(survey)


@router.delete("/{survey_id}", status_code=204)
async def delete_survey(
    survey_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a survey and all associated data."""
    service = SurveyService(db)
    await service.delete_survey(survey_id, current_user.id)
