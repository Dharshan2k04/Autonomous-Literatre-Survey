"""Agent 2: Citation Explorer — Parallel paper retrieval, deduplication, and ranking."""

from __future__ import annotations

import asyncio
from typing import Any

from rapidfuzz import fuzz

from app.core.logging import get_logger
from app.external.arxiv_client import ArxivClient
from app.external.crossref_client import CrossrefClient
from app.external.semantic_scholar import SemanticScholarClient
from app.schemas.paper import PaperSearchResult

logger = get_logger(__name__)

# Deduplication thresholds
TITLE_SIMILARITY_THRESHOLD = 85  # Fuzzy match percentage


class CitationExplorerAgent:
    """Retrieves papers from multiple sources, deduplicates, and ranks them."""

    def __init__(self):
        self.semantic_scholar = SemanticScholarClient()
        self.arxiv = ArxivClient()
        self.crossref = CrossrefClient()

    async def search_all_sources(
        self,
        queries: list[str],
        papers_per_query: int = 20,
        max_total: int = 50,
    ) -> list[PaperSearchResult]:
        """Execute parallel searches across all sources for all queries.

        Args:
            queries: List of search query strings.
            papers_per_query: Max papers per source per query.
            max_total: Maximum total papers after dedup and ranking.

        Returns:
            Deduplicated and ranked list of papers.
        """
        logger.info("citation_explorer_start", num_queries=len(queries))

        # Create tasks for all queries across all sources
        tasks = []
        for query in queries:
            tasks.append(self._safe_search(self.semantic_scholar, query, papers_per_query))
            tasks.append(self._safe_search(self.arxiv, query, papers_per_query))
            tasks.append(self._safe_search(self.crossref, query, papers_per_query))

        # Execute all searches concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten results, filtering out errors
        all_papers: list[PaperSearchResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning("search_source_failed", task_index=i, error=str(result))
                continue
            if isinstance(result, list):
                all_papers.extend(result)

        logger.info("citation_explorer_raw_count", count=len(all_papers))

        # Deduplicate
        unique_papers = self._deduplicate(all_papers)
        logger.info("citation_explorer_after_dedup", count=len(unique_papers))

        # Rank by citation count and recency
        ranked_papers = self._rank_papers(unique_papers)

        # Limit to max_total
        final_papers = ranked_papers[:max_total]
        logger.info("citation_explorer_final", count=len(final_papers))

        return final_papers

    async def _safe_search(
        self, client: Any, query: str, limit: int
    ) -> list[PaperSearchResult]:
        """Safely execute a search, returning empty list on failure."""
        try:
            return await client.search_papers(query, limit=limit)
        except Exception as e:
            logger.warning(
                "search_failed",
                source=type(client).__name__,
                query=query,
                error=str(e),
            )
            return []

    def _deduplicate(self, papers: list[PaperSearchResult]) -> list[PaperSearchResult]:
        """Remove duplicate papers using DOI matching and title similarity."""
        seen_dois: set[str] = set()
        seen_titles: list[str] = []
        unique: list[PaperSearchResult] = []

        for paper in papers:
            # Skip papers with no title
            if not paper.title or len(paper.title.strip()) < 5:
                continue

            # DOI-based dedup
            if paper.doi:
                doi_lower = paper.doi.lower().strip()
                if doi_lower in seen_dois:
                    continue
                seen_dois.add(doi_lower)

            # Title-based fuzzy dedup
            title_normalized = paper.title.lower().strip()
            is_duplicate = False
            for seen_title in seen_titles:
                if fuzz.ratio(title_normalized, seen_title) >= TITLE_SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break

            if not is_duplicate:
                seen_titles.append(title_normalized)
                unique.append(paper)

        return unique

    def _rank_papers(self, papers: list[PaperSearchResult]) -> list[PaperSearchResult]:
        """Rank papers by a composite score of citation count and recency."""
        import datetime

        current_year = datetime.datetime.now().year

        def score(paper: PaperSearchResult) -> float:
            # Citation score: log scale to prevent extreme outliers
            import math
            citation_score = math.log1p(paper.citation_count) * 10

            # Recency score: papers from last 5 years get a boost
            recency_score = 0.0
            if paper.year:
                years_old = max(0, current_year - paper.year)
                recency_score = max(0, 20 - years_old * 2)  # 20 points for this year, -2/year

            # Abstract availability bonus
            abstract_score = 5.0 if paper.abstract else 0.0

            return citation_score + recency_score + abstract_score

        return sorted(papers, key=score, reverse=True)
