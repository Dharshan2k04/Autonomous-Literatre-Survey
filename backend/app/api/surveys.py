"""
Survey REST API endpoints.
"""
from __future__ import annotations

import asyncio
import re
import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.survey import Survey, Paper, SurveyStatus
from app.agents import (
    run_query_strategist,
    run_citation_explorer,
    run_ieee_formatter,
    run_survey_architect,
)
from app.services.pinecone_service import upsert_papers
from app.services.redis_service import cache_set, cache_get

log = structlog.get_logger()
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class CreateSurveyRequest(BaseModel):
    topic: str

    @field_validator("topic")
    @classmethod
    def topic_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("topic must not be empty")
        if len(v) > 512:
            raise ValueError("topic must be ≤ 512 characters")
        return v


class PaperOut(BaseModel):
    id: int
    title: str
    authors: Optional[List[str]]
    year: Optional[int]
    venue: Optional[str]
    doi: Optional[str]
    url: Optional[str]
    citation_count: int
    ieee_number: Optional[int]
    ieee_citation: Optional[str]
    summary: Optional[str]
    cluster_label: Optional[str]

    model_config = {"from_attributes": True}


class SurveyOut(BaseModel):
    id: int
    topic: str
    status: SurveyStatus
    sub_queries: Optional[List[str]]
    research_gaps: Optional[List[str]]
    survey_markdown: Optional[str]
    papers: List[PaperOut] = []

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Background workflow
# ---------------------------------------------------------------------------

async def _run_survey_pipeline(survey_id: int, topic: str) -> None:
    """Full 4-stage pipeline running in the background."""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        async def _update_status(status: SurveyStatus, **kwargs):
            survey = await db.get(Survey, survey_id)
            if survey:
                survey.status = status
                for k, v in kwargs.items():
                    setattr(survey, k, v)
                await db.commit()

        try:
            # Stage 1 – Query Strategist
            await _update_status(SurveyStatus.querying)
            sub_queries = await run_query_strategist(topic)
            await _update_status(SurveyStatus.querying, sub_queries=sub_queries)

            # Stage 2 – Citation Explorer
            await _update_status(SurveyStatus.fetching)
            raw_papers = await run_citation_explorer(sub_queries)

            # Stage 3 – IEEE Formatter (+ embedding)
            await _update_status(SurveyStatus.formatting)
            formatted_papers = await run_ieee_formatter(raw_papers, topic)

            # Persist papers to DB
            namespace = f"survey-{survey_id}"
            for p_data in formatted_papers:
                paper = Paper(
                    survey_id=survey_id,
                    title=p_data.get("title", ""),
                    authors=p_data.get("authors"),
                    year=p_data.get("year"),
                    venue=p_data.get("venue"),
                    doi=p_data.get("doi"),
                    arxiv_id=p_data.get("arxiv_id"),
                    url=p_data.get("url"),
                    abstract=p_data.get("abstract"),
                    citation_count=p_data.get("citation_count", 0),
                    source=p_data.get("source"),
                    ieee_citation=p_data.get("ieee_citation"),
                    ieee_number=p_data.get("ieee_number"),
                    summary=p_data.get("summary"),
                )
                db.add(paper)
            await db.commit()

            # Upsert embeddings to Pinecone
            await _update_status(SurveyStatus.embedding, pinecone_namespace=namespace)
            await upsert_papers(formatted_papers, namespace)

            # Stage 4 – Survey Architect
            await _update_status(SurveyStatus.compiling)
            clustered, gaps, survey_md = await run_survey_architect(
                formatted_papers, topic, namespace
            )

            # Update cluster labels
            for p_data in clustered:
                stmt = (
                    select(Paper)
                    .where(Paper.survey_id == survey_id)
                    .where(Paper.ieee_number == p_data.get("ieee_number"))
                )
                result = await db.execute(stmt)
                paper = result.scalar_one_or_none()
                if paper:
                    paper.cluster_label = p_data.get("cluster_label")
            await db.commit()

            await _update_status(
                SurveyStatus.completed,
                survey_markdown=survey_md,
                research_gaps=gaps,
            )
            log.info("Survey pipeline completed", survey_id=survey_id)

            # Cache survey for fast retrieval
            await cache_set(f"survey:{survey_id}", {"status": "completed"}, ttl=86400)

        except Exception as exc:
            log.error("Survey pipeline failed", survey_id=survey_id, error=str(exc))
            await _update_status(SurveyStatus.failed, error_message=str(exc))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=SurveyOut, status_code=status.HTTP_202_ACCEPTED)
async def create_survey(
    body: CreateSurveyRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Create a new literature survey and kick off the async pipeline."""
    survey = Survey(topic=body.topic, status=SurveyStatus.pending)
    db.add(survey)
    await db.commit()
    await db.refresh(survey)

    background_tasks.add_task(_run_survey_pipeline, survey.id, body.topic)
    log.info("Survey created", survey_id=survey.id)
    return survey


@router.get("/", response_model=List[SurveyOut])
async def list_surveys(db: AsyncSession = Depends(get_db)):
    """List all surveys."""
    result = await db.execute(select(Survey).order_by(Survey.created_at.desc()))
    return result.scalars().all()


@router.get("/{survey_id}", response_model=SurveyOut)
async def get_survey(survey_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single survey with its papers."""
    survey = await db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    # Eager load papers
    result = await db.execute(
        select(Paper).where(Paper.survey_id == survey_id).order_by(Paper.ieee_number)
    )
    survey.papers = result.scalars().all()
    return survey


@router.delete("/{survey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_survey(survey_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a survey and its papers."""
    survey = await db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    await db.delete(survey)
    await db.commit()
