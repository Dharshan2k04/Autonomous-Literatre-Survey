"""Semantic Scholar API client with retry and rate limiting."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings
from app.core.logging import get_logger
from app.schemas.paper import PaperSearchResult

logger = get_logger(__name__)
settings = get_settings()

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,title,authors,abstract,year,venue,externalIds,url,citationCount,openAccessPdf"


class SemanticScholarClient:
    """Async client for Semantic Scholar API."""

    def __init__(self):
        self.headers = {}
        if settings.SEMANTIC_SCHOLAR_API_KEY:
            self.headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    )
    async def search_papers(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> list[PaperSearchResult]:
        """Search for papers by query string."""
        logger.info("semantic_scholar_search", query=query, limit=limit)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{BASE_URL}/paper/search",
                params={
                    "query": query,
                    "limit": min(limit, 100),
                    "offset": offset,
                    "fields": FIELDS,
                },
                headers=self.headers,
            )
            response.raise_for_status()

        data = response.json()
        papers = []

        for item in data.get("data", []):
            try:
                authors = [a.get("name", "") for a in item.get("authors", [])]
                external_ids = item.get("externalIds", {}) or {}
                open_access = item.get("openAccessPdf", {}) or {}

                paper = PaperSearchResult(
                    title=item.get("title", ""),
                    authors=authors,
                    abstract=item.get("abstract"),
                    year=item.get("year"),
                    venue=item.get("venue"),
                    doi=external_ids.get("DOI"),
                    arxiv_id=external_ids.get("ArXiv"),
                    semantic_scholar_id=item.get("paperId"),
                    url=item.get("url"),
                    pdf_url=open_access.get("url"),
                    source="semantic_scholar",
                    citation_count=item.get("citationCount", 0) or 0,
                )
                papers.append(paper)
            except Exception as e:
                logger.warning("semantic_scholar_parse_error", error=str(e), paper_id=item.get("paperId"))
                continue

        logger.info("semantic_scholar_results", query=query, count=len(papers))
        return papers

    async def get_paper_details(self, paper_id: str) -> dict[str, Any] | None:
        """Get detailed information for a specific paper."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{BASE_URL}/paper/{paper_id}",
                    params={"fields": FIELDS},
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning("semantic_scholar_detail_error", paper_id=paper_id, error=str(e))
            return None
