"""Crossref API client."""

from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings
from app.core.logging import get_logger
from app.schemas.paper import PaperSearchResult

logger = get_logger(__name__)
settings = get_settings()

BASE_URL = "https://api.crossref.org/works"


class CrossrefClient:
    """Async client for the Crossref REST API."""

    def __init__(self):
        self.headers = {"User-Agent": f"AutonomousLiteratureSurvey/1.0 (mailto:{settings.CROSSREF_EMAIL})"}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    )
    async def search_papers(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> list[PaperSearchResult]:
        """Search Crossref for papers matching the query."""
        logger.info("crossref_search", query=query, limit=limit)

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                BASE_URL,
                params={
                    "query": query,
                    "rows": min(limit, 50),
                    "offset": offset,
                    "sort": "relevance",
                    "order": "desc",
                    "select": "DOI,title,author,abstract,published-print,published-online,"
                              "container-title,is-referenced-by-count,URL,link",
                },
                headers=self.headers,
            )
            response.raise_for_status()

        data = response.json()
        papers = []

        for item in data.get("message", {}).get("items", []):
            try:
                paper = self._parse_item(item)
                if paper:
                    papers.append(paper)
            except Exception as e:
                logger.warning("crossref_parse_error", error=str(e), doi=item.get("DOI"))
                continue

        logger.info("crossref_results", query=query, count=len(papers))
        return papers

    def _parse_item(self, item: dict) -> PaperSearchResult | None:
        """Parse a single Crossref work item."""
        title_list = item.get("title", [])
        if not title_list:
            return None
        title = title_list[0]

        # Authors
        authors = []
        for author in item.get("author", []):
            given = author.get("given", "")
            family = author.get("family", "")
            if given and family:
                authors.append(f"{given} {family}")
            elif family:
                authors.append(family)

        # Year from published-print or published-online
        year = None
        for date_field in ("published-print", "published-online"):
            date_parts = item.get(date_field, {}).get("date-parts", [[]])
            if date_parts and date_parts[0] and date_parts[0][0]:
                year = date_parts[0][0]
                break

        # Abstract (often contains JATS XML tags)
        abstract = item.get("abstract", "")
        if abstract:
            # Strip JATS XML tags
            import re
            abstract = re.sub(r"<[^>]+>", "", abstract).strip()

        # Venue
        venue_list = item.get("container-title", [])
        venue = venue_list[0] if venue_list else None

        # PDF URL
        pdf_url = None
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL")
                break

        return PaperSearchResult(
            title=title,
            authors=authors,
            abstract=abstract if abstract else None,
            year=year,
            venue=venue,
            doi=item.get("DOI"),
            url=item.get("URL"),
            pdf_url=pdf_url,
            source="crossref",
            citation_count=item.get("is-referenced-by-count", 0) or 0,
        )
