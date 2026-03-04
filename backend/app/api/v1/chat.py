"""Chat API route — RAG-based chat over a survey's paper collection."""

from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.config import get_settings
from app.core.logging import get_logger
from app.database import get_db
from app.models.paper import Paper
from app.models.survey import Survey
from app.models.user import User
from app.schemas.survey import ChatResponse, SurveyChatMessage
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import get_llm_service
from app.services.vector_store import VectorStoreService

router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()

CHAT_SYSTEM_PROMPT = """You are an expert research assistant helping a user understand their literature survey.
You have access to a collection of academic papers. When answering questions:

1. Cite papers using their IEEE numbers like [1], [2], etc.
2. Be precise and factual based on the paper information provided
3. If the answer is not in the provided papers, say so
4. Synthesize information across multiple papers when relevant
5. Be concise but thorough

Context papers will be provided as retrieved documents."""


@router.post("", response_model=ChatResponse)
async def chat_with_survey(
    survey_id: UUID,
    body: SurveyChatMessage,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Chat with a survey's paper collection using RAG retrieval."""
    # Verify survey ownership
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.user_id == current_user.id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        from app.core.exceptions import NotFoundError
        raise NotFoundError("Survey", survey_id)

    llm = get_llm_service()
    embedding_service = EmbeddingService()
    vector_store = VectorStoreService()

    cited_papers = []
    context_text = ""

    # RAG retrieval from Pinecone if available
    if (
        embedding_service.available
        and vector_store.available
        and survey.pinecone_namespace
    ):
        try:
            query_embedding = await embedding_service.embed_text(body.message)
            results = await vector_store.query(
                namespace=survey.pinecone_namespace,
                query_embedding=query_embedding,
                top_k=8,
            )

            # Build context from retrieved papers
            context_parts = []
            for match in results:
                meta = match.get("metadata", {})
                context_parts.append(
                    f"Paper: {meta.get('title', 'Unknown')}\n"
                    f"Authors: {meta.get('authors', 'Unknown')}\n"
                    f"Year: {meta.get('year', 'Unknown')}\n"
                    f"Relevance Score: {match.get('score', 0):.3f}"
                )
                cited_papers.append(meta)

            context_text = "\n---\n".join(context_parts)
        except Exception as e:
            logger.warning("rag_retrieval_error", error=str(e))

    # Fallback: use papers from DB if no vector results
    if not context_text:
        db_papers = await db.execute(
            select(Paper)
            .where(Paper.survey_id == survey_id)
            .order_by(Paper.ieee_number.asc().nullslast())
            .limit(15)
        )
        papers = db_papers.scalars().all()
        context_parts = []
        for p in papers:
            context_parts.append(
                f"[{p.ieee_number or '?'}] {p.title}\n"
                f"Authors: {', '.join(p.authors[:3]) if p.authors else 'Unknown'}\n"
                f"Year: {p.year or 'Unknown'}\n"
                f"Summary: {p.summary or p.abstract[:200] if p.abstract else 'No summary'}"
            )
            cited_papers.append({
                "title": p.title,
                "ieee_number": p.ieee_number,
                "year": p.year,
            })
        context_text = "\n---\n".join(context_parts)

    prompt = f"""Research Topic: {survey.topic}

Retrieved Papers:
{context_text}

User Question: {body.message}

Provide a comprehensive answer citing specific papers by their IEEE numbers [N]."""

    answer = await llm.generate(
        prompt=prompt,
        system_prompt=CHAT_SYSTEM_PROMPT,
        temperature=0.4,
        max_tokens=2000,
    )

    return ChatResponse(
        answer=answer,
        cited_papers=cited_papers[:10],
        sources=[f"[{p.get('ieee_number', '?')}] {p.get('title', '')}" for p in cited_papers[:10]],
    )
