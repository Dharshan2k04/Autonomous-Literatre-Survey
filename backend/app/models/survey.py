"""Survey model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SurveyStatus(str, enum.Enum):
    PENDING = "pending"
    QUERY_EXPANSION = "query_expansion"
    PAPER_RETRIEVAL = "paper_retrieval"
    FORMATTING = "formatting"
    SURVEY_GENERATION = "survey_generation"
    COMPLETED = "completed"
    FAILED = "failed"


class Survey(Base):
    __tablename__ = "surveys"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[SurveyStatus] = mapped_column(
        Enum(SurveyStatus), default=SurveyStatus.PENDING, nullable=False
    )
    progress: Mapped[int] = mapped_column(Integer, default=0)

    # Agent outputs 
    expanded_queries: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    paper_count: Mapped[int] = mapped_column(Integer, default=0)
    pinecone_namespace: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Final output  
    survey_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    bibliography: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    taxonomy: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User", back_populates="surveys")
    papers = relationship("Paper", back_populates="survey", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Survey {self.id} - {self.topic[:50]}>"
