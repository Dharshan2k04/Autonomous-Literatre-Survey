"""Paper schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PaperResponse(BaseModel):
    id: UUID
    title: str
    authors: list | None = None
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    source: str
    citation_count: int = 0
    relevance_score: float = 0.0
    ieee_number: int | None = None
    ieee_citation: str | None = None
    summary: str | None = None
    cluster_label: str | None = None
    cluster_id: int | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaperListResponse(BaseModel):
    papers: list[PaperResponse]
    total: int


class PaperSearchResult(BaseModel):
    """Raw paper data from external APIs before persistence."""
    title: str
    authors: list[str] = []
    abstract: str | None = None
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    semantic_scholar_id: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    source: str
    citation_count: int = 0
