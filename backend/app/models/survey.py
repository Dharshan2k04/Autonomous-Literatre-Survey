"""SQLAlchemy ORM models."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class SurveyStatus(str, enum.Enum):
    pending = "pending"
    querying = "querying"
    fetching = "fetching"
    embedding = "embedding"
    formatting = "formatting"
    compiling = "compiling"
    completed = "completed"
    failed = "failed"


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[SurveyStatus] = mapped_column(
        SAEnum(SurveyStatus), default=SurveyStatus.pending, nullable=False
    )
    sub_queries: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    pinecone_namespace: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    survey_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    research_gaps: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    papers: Mapped[List["Paper"]] = relationship(
        "Paper", back_populates="survey", cascade="all, delete-orphan"
    )


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    survey_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    authors: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    doi: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, index=True)
    arxiv_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # IEEE formatted fields
    ieee_citation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ieee_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Clustering
    cluster_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    survey: Mapped["Survey"] = relationship("Survey", back_populates="papers")
