"""Survey business logic service."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.paper import Paper
from app.models.survey import Survey, SurveyStatus

logger = get_logger(__name__)


class SurveyService:
    """Business logic for survey CRUD and retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_survey(self, user_id: uuid.UUID, topic: str) -> Survey:
        """Create a new survey record."""
        survey = Survey(
            user_id=user_id,
            topic=topic,
            status=SurveyStatus.PENDING,
            pinecone_namespace=f"survey-{uuid.uuid4()}",
        )
        self.db.add(survey)
        await self.db.flush()
        await self.db.refresh(survey)
        logger.info("survey_created", survey_id=str(survey.id), topic=topic)
        return survey

    async def get_survey(self, survey_id: uuid.UUID, user_id: uuid.UUID) -> Survey:
        """Get a survey by ID, ensuring it belongs to the user."""
        result = await self.db.execute(
            select(Survey).where(Survey.id == survey_id, Survey.user_id == user_id)
        )
        survey = result.scalar_one_or_none()
        if not survey:
            raise NotFoundError("Survey", survey_id)
        return survey

    async def get_survey_with_papers(
        self, survey_id: uuid.UUID, user_id: uuid.UUID
    ) -> Survey:
        """Get a survey with its papers loaded."""
        result = await self.db.execute(
            select(Survey)
            .options(selectinload(Survey.papers))
            .where(Survey.id == survey_id, Survey.user_id == user_id)
        )
        survey = result.scalar_one_or_none()
        if not survey:
            raise NotFoundError("Survey", survey_id)
        return survey

    async def list_surveys(
        self, user_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> tuple[list[Survey], int]:
        """List surveys for a user with pagination."""
        # Count
        count_result = await self.db.execute(
            select(func.count(Survey.id)).where(Survey.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Fetch
        result = await self.db.execute(
            select(Survey)
            .where(Survey.user_id == user_id)
            .order_by(Survey.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        surveys = list(result.scalars().all())
        return surveys, total

    async def delete_survey(self, survey_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a survey and its associated papers."""
        survey = await self.get_survey(survey_id, user_id)
        await self.db.delete(survey)
        await self.db.flush()
        logger.info("survey_deleted", survey_id=str(survey_id))

    async def get_papers(
        self, survey_id: uuid.UUID, user_id: uuid.UUID
    ) -> list[Paper]:
        """Get all papers for a survey."""
        # Verify ownership
        await self.get_survey(survey_id, user_id)

        result = await self.db.execute(
            select(Paper)
            .where(Paper.survey_id == survey_id)
            .order_by(Paper.ieee_number.asc().nullslast(), Paper.citation_count.desc())
        )
        return list(result.scalars().all())
