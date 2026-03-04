"""Main LangGraph agent workflow — orchestrates the four-stage pipeline."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.citation_explorer import CitationExplorerAgent
from app.agents.ieee_formatter import IEEEFormatterAgent
from app.agents.query_strategist import QueryStrategistAgent
from app.agents.survey_architect import SurveyArchitectAgent
from app.core.logging import get_logger
from app.models.paper import Paper
from app.models.survey import Survey, SurveyStatus
from app.services.cache_service import CacheService
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import get_llm_service
from app.services.vector_store import VectorStoreService

logger = get_logger(__name__)


class SurveyState(TypedDict, total=False):
    """State passed through the LangGraph workflow."""
    survey_id: str
    user_id: str
    topic: str
    status: str
    progress: int
    error: str | None
    # Agent outputs
    expanded_queries: dict | None
    raw_papers: list[dict]
    formatted_citations: list[dict]
    taxonomy: dict | None
    survey_markdown: str | None


class SurveyWorkflow:
    """Orchestrates the four-stage literature survey pipeline.

    Stage 1: Query Strategist — expand topic into sub-queries
    Stage 2: Citation Explorer — parallel paper retrieval + dedup + rank
    Stage 3: IEEE Formatter — generate citations and summaries
    Stage 4: Survey Architect — cluster, identify gaps, generate survey
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = get_llm_service()
        self.embedding_service = EmbeddingService()
        self.vector_store = VectorStoreService()
        self.cache = CacheService()

    async def run(self, survey_id: str, topic: str, user_id: str) -> dict[str, Any]:
        """Execute the full survey pipeline.

        This is the main entry point, called from the API route.
        """
        logger.info("workflow_start", survey_id=survey_id, topic=topic)

        state: SurveyState = {
            "survey_id": survey_id,
            "user_id": user_id,
            "topic": topic,
            "status": SurveyStatus.PENDING,
            "progress": 0,
            "error": None,
            "expanded_queries": None,
            "raw_papers": [],
            "formatted_citations": [],
            "taxonomy": None,
            "survey_markdown": None,
        }

        try:
            # Stage 1: Query Expansion
            state = await self._stage_query_expansion(state)

            # Stage 2: Paper Retrieval
            state = await self._stage_paper_retrieval(state)

            # Stage 3: IEEE Formatting
            state = await self._stage_formatting(state)

            # Stage 4: Survey Generation
            state = await self._stage_survey_generation(state)

            # Mark complete
            await self._update_survey_status(
                survey_id, SurveyStatus.COMPLETED, 100, completed=True
            )
            state["status"] = SurveyStatus.COMPLETED
            state["progress"] = 100

            logger.info("workflow_complete", survey_id=survey_id)

        except Exception as e:
            logger.error("workflow_failed", survey_id=survey_id, error=str(e))
            state["error"] = str(e)
            state["status"] = SurveyStatus.FAILED
            await self._update_survey_status(
                survey_id, SurveyStatus.FAILED, state["progress"], error=str(e)
            )

        return state

    async def _stage_query_expansion(self, state: SurveyState) -> SurveyState:
        """Stage 1: Expand the research topic into sub-queries."""
        logger.info("stage_1_start", survey_id=state["survey_id"])
        await self._update_survey_status(
            state["survey_id"], SurveyStatus.QUERY_EXPANSION, 10
        )
        await self._broadcast_progress(state["survey_id"], SurveyStatus.QUERY_EXPANSION, 10,
                                        "Expanding research topic into targeted sub-queries...")

        agent = QueryStrategistAgent(self.llm)
        result = await agent.expand_query(state["topic"])

        state["expanded_queries"] = result
        state["progress"] = 20

        # Save to database
        await self._update_survey_field(state["survey_id"], "expanded_queries", result)
        await self._broadcast_progress(state["survey_id"], SurveyStatus.QUERY_EXPANSION, 20,
                                        f"Generated {len(result.get('sub_queries', []))} sub-queries")

        logger.info("stage_1_complete", survey_id=state["survey_id"])
        return state

    async def _stage_paper_retrieval(self, state: SurveyState) -> SurveyState:
        """Stage 2: Retrieve papers from multiple sources."""
        logger.info("stage_2_start", survey_id=state["survey_id"])
        await self._update_survey_status(
            state["survey_id"], SurveyStatus.PAPER_RETRIEVAL, 30
        )
        await self._broadcast_progress(state["survey_id"], SurveyStatus.PAPER_RETRIEVAL, 30,
                                        "Searching Semantic Scholar, arXiv, and Crossref...")

        queries = [q["query"] for q in state["expanded_queries"].get("sub_queries", [])]

        agent = CitationExplorerAgent()
        papers = await agent.search_all_sources(queries, papers_per_query=20, max_total=50)

        # Convert to dicts for state
        papers_data = [p.model_dump() for p in papers]
        state["raw_papers"] = papers_data

        # Save papers to database
        namespace = f"survey-{state['survey_id']}"
        await self._save_papers_to_db(state["survey_id"], papers)

        # Embed and store in Pinecone if available
        if self.embedding_service.available and self.vector_store.available:
            await self._embed_and_store(namespace, papers)
            await self._update_survey_field(state["survey_id"], "pinecone_namespace", namespace)

        state["progress"] = 50
        await self._update_survey_field(state["survey_id"], "paper_count", len(papers))
        await self._broadcast_progress(state["survey_id"], SurveyStatus.PAPER_RETRIEVAL, 50,
                                        f"Retrieved and ranked {len(papers)} unique papers")

        logger.info("stage_2_complete", survey_id=state["survey_id"], papers=len(papers))
        return state

    async def _stage_formatting(self, state: SurveyState) -> SurveyState:
        """Stage 3: Generate IEEE citations and summaries."""
        logger.info("stage_3_start", survey_id=state["survey_id"])
        await self._update_survey_status(
            state["survey_id"], SurveyStatus.FORMATTING, 60
        )
        await self._broadcast_progress(state["survey_id"], SurveyStatus.FORMATTING, 60,
                                        "Generating IEEE citations and contextual summaries...")

        from app.schemas.paper import PaperSearchResult
        papers = [PaperSearchResult(**p) for p in state["raw_papers"]]

        agent = IEEEFormatterAgent(self.llm)
        citations = await agent.format_papers(papers, state["topic"])
        state["formatted_citations"] = citations

        # Update papers in DB with IEEE info
        await self._update_papers_with_citations(state["survey_id"], citations)

        state["progress"] = 70
        await self._broadcast_progress(state["survey_id"], SurveyStatus.FORMATTING, 70,
                                        f"Formatted {len(citations)} IEEE citations with summaries")

        logger.info("stage_3_complete", survey_id=state["survey_id"])
        return state

    async def _stage_survey_generation(self, state: SurveyState) -> SurveyState:
        """Stage 4: Cluster papers, generate taxonomy, and compile survey."""
        logger.info("stage_4_start", survey_id=state["survey_id"])
        await self._update_survey_status(
            state["survey_id"], SurveyStatus.SURVEY_GENERATION, 80
        )
        await self._broadcast_progress(state["survey_id"], SurveyStatus.SURVEY_GENERATION, 80,
                                        "Clustering papers and generating survey...")

        agent = SurveyArchitectAgent(self.llm)

        # Prepare papers with citation info
        papers_with_citations = []
        for idx, paper_data in enumerate(state["raw_papers"]):
            paper_info = {**paper_data}
            # Find matching citation
            matching_citation = next(
                (c for c in state["formatted_citations"] if c.get("ieee_number") == idx + 1),
                None,
            )
            if matching_citation:
                paper_info["ieee_number"] = matching_citation["ieee_number"]
                paper_info["summary"] = matching_citation.get("summary", "")
            else:
                paper_info["ieee_number"] = idx + 1
            papers_with_citations.append(paper_info)

        # Cluster papers (use simple embeddings if available, else random)
        embeddings = []
        if self.embedding_service.available:
            try:
                texts = [
                    f"{p.get('title', '')} {p.get('abstract', '')}"
                    for p in papers_with_citations
                ]
                embeddings = await self.embedding_service.embed_texts(texts)
            except Exception as e:
                logger.warning("clustering_embedding_error", error=str(e))

        if not embeddings:
            # Fallback: random embeddings for clustering
            import numpy as np
            rng = np.random.default_rng(42)
            embeddings = rng.random((len(papers_with_citations), 64)).tolist()

        clustered = await agent.cluster_papers(papers_with_citations, embeddings)

        # Generate taxonomy
        taxonomy = await agent.generate_taxonomy(clustered, state["topic"])
        state["taxonomy"] = taxonomy
        await self._update_survey_field(state["survey_id"], "taxonomy", taxonomy)

        await self._broadcast_progress(state["survey_id"], SurveyStatus.SURVEY_GENERATION, 90,
                                        "Compiling structured survey document...")

        # Generate final survey
        survey_md = await agent.generate_survey(
            topic=state["topic"],
            papers=clustered,
            taxonomy=taxonomy,
            citations=state["formatted_citations"],
        )
        state["survey_markdown"] = survey_md

        # Save to database
        await self._update_survey_field(state["survey_id"], "survey_markdown", survey_md)
        await self._update_survey_field(
            state["survey_id"], "bibliography",
            {"citations": state["formatted_citations"]}
        )

        logger.info("stage_4_complete", survey_id=state["survey_id"])
        return state

    # ---- Helper methods ----

    async def _save_papers_to_db(
        self, survey_id: str, papers: list
    ) -> None:
        """Persist papers to the database."""
        for paper in papers:
            db_paper = Paper(
                survey_id=uuid.UUID(survey_id),
                title=paper.title,
                authors=paper.authors,
                abstract=paper.abstract,
                year=paper.year,
                venue=paper.venue,
                doi=paper.doi,
                arxiv_id=paper.arxiv_id,
                semantic_scholar_id=paper.semantic_scholar_id,
                url=paper.url,
                pdf_url=paper.pdf_url,
                source=paper.source,
                citation_count=paper.citation_count,
            )
            self.db.add(db_paper)
        await self.db.flush()

    async def _embed_and_store(self, namespace: str, papers: list) -> None:
        """Embed papers and store in Pinecone."""
        try:
            texts = [f"{p.title}\n\n{p.abstract or ''}" for p in papers]
            embeddings = await self.embedding_service.embed_texts(texts)

            paper_ids = [str(uuid.uuid4()) for _ in papers]
            metadata_list = [
                {
                    "title": p.title,
                    "authors": ", ".join(p.authors[:5]) if p.authors else "",
                    "year": p.year or 0,
                    "source": p.source,
                    "doi": p.doi or "",
                    "citation_count": p.citation_count,
                }
                for p in papers
            ]

            await self.vector_store.upsert_papers(namespace, paper_ids, embeddings, metadata_list)
        except Exception as e:
            logger.warning("embed_and_store_error", error=str(e))

    async def _update_papers_with_citations(
        self, survey_id: str, citations: list[dict]
    ) -> None:
        """Update papers in DB with IEEE citation info."""
        result = await self.db.execute(
            select(Paper)
            .where(Paper.survey_id == uuid.UUID(survey_id))
            .order_by(Paper.created_at)
        )
        db_papers = result.scalars().all()

        for idx, db_paper in enumerate(db_papers):
            matching = next(
                (c for c in citations if c.get("ieee_number") == idx + 1), None
            )
            if matching:
                db_paper.ieee_number = matching["ieee_number"]
                db_paper.ieee_citation = matching.get("ieee_citation")
                db_paper.summary = matching.get("summary")
        await self.db.flush()

    async def _update_survey_status(
        self,
        survey_id: str,
        status: SurveyStatus,
        progress: int,
        error: str | None = None,
        completed: bool = False,
    ) -> None:
        """Update survey status in the database."""
        result = await self.db.execute(
            select(Survey).where(Survey.id == uuid.UUID(survey_id))
        )
        survey = result.scalar_one_or_none()
        if survey:
            survey.status = status
            survey.progress = progress
            if error:
                survey.error_message = error
            if completed:
                survey.completed_at = datetime.now(timezone.utc)
            await self.db.flush()

    async def _update_survey_field(self, survey_id: str, field: str, value: Any) -> None:
        """Update a specific field on the survey."""
        result = await self.db.execute(
            select(Survey).where(Survey.id == uuid.UUID(survey_id))
        )
        survey = result.scalar_one_or_none()
        if survey:
            setattr(survey, field, value)
            await self.db.flush()

    async def _broadcast_progress(
        self, survey_id: str, status: SurveyStatus, progress: int, message: str
    ) -> None:
        """Broadcast progress update via cache (consumed by WebSocket)."""
        await self.cache.set_survey_progress(
            survey_id,
            {
                "survey_id": survey_id,
                "status": status.value,
                "progress": progress,
                "message": message,
            },
        )
