"""Paper model."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    survey_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Identifiers
    doi: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    arxiv_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    semantic_scholar_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Metadata
    title: Mapped[str] = mapped_column(Text, nullable=False)
    authors: Mapped[list | None] = mapped_column(JSON, nullable=True)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    venue: Mapped[str | None] = mapped_column(String(500), nullable=True)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # semantic_scholar, arxiv, crossref

    # Citation & ranking
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)

    # IEEE formatting
    ieee_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ieee_citation: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Clustering
    cluster_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cluster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    survey = relationship("Survey", back_populates="papers")

    def __repr__(self) -> str:
        return f"<Paper {self.title[:50]}>"
