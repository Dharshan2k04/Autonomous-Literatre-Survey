"""arXiv API client using the Atom feed."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger
from app.schemas.paper import PaperSearchResult

logger = get_logger(__name__)

BASE_URL = "http://export.arxiv.org/api/query"
ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"


class ArxivClient:
    """Async client for the arXiv API."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    )
    async def search_papers(
        self, query: str, limit: int = 20, offset: int = 0
    ) -> list[PaperSearchResult]:
        """Search arXiv for papers matching the query."""
        logger.info("arxiv_search", query=query, limit=limit)

        # Build a search query appropriate for arXiv
        search_query = f'all:"{query}"'

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                BASE_URL,
                params={
                    "search_query": search_query,
                    "start": offset,
                    "max_results": min(limit, 50),
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                },
            )
            response.raise_for_status()

        papers = self._parse_atom_feed(response.text)
        logger.info("arxiv_results", query=query, count=len(papers))
        return papers

    def _parse_atom_feed(self, xml_text: str) -> list[PaperSearchResult]:
        """Parse arXiv Atom XML feed into paper results."""
        papers = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError as e:
            logger.error("arxiv_xml_parse_error", error=str(e))
            return papers

        for entry in root.findall(f"{ATOM_NS}entry"):
            try:
                title = entry.findtext(f"{ATOM_NS}title", "").strip().replace("\n", " ")
                abstract = entry.findtext(f"{ATOM_NS}summary", "").strip().replace("\n", " ")

                # Authors
                authors = []
                for author in entry.findall(f"{ATOM_NS}author"):
                    name = author.findtext(f"{ATOM_NS}name", "")
                    if name:
                        authors.append(name)

                # Extract arXiv ID from the entry id URL
                entry_id = entry.findtext(f"{ATOM_NS}id", "")
                arxiv_id = self._extract_arxiv_id(entry_id)

                # Published year
                published = entry.findtext(f"{ATOM_NS}published", "")
                year = int(published[:4]) if published else None

                # Links
                pdf_url = None
                url = entry_id
                for link in entry.findall(f"{ATOM_NS}link"):
                    if link.get("title") == "pdf":
                        pdf_url = link.get("href")

                # DOI
                doi = entry.findtext(f"{ARXIV_NS}doi")

                # Category as venue
                primary_cat = entry.find(f"{ARXIV_NS}primary_category")
                venue = primary_cat.get("term", "") if primary_cat is not None else ""

                paper = PaperSearchResult(
                    title=title,
                    authors=authors,
                    abstract=abstract,
                    year=year,
                    venue=venue,
                    doi=doi,
                    arxiv_id=arxiv_id,
                    url=url,
                    pdf_url=pdf_url,
                    source="arxiv",
                    citation_count=0,  # arXiv doesn't provide citation counts
                )
                papers.append(paper)
            except Exception as e:
                logger.warning("arxiv_entry_parse_error", error=str(e))
                continue

        return papers

    @staticmethod
    def _extract_arxiv_id(entry_id: str) -> str | None:
        """Extract arXiv ID from URL like http://arxiv.org/abs/2301.12345v1."""
        match = re.search(r"arxiv\.org/abs/(.+?)(?:v\d+)?$", entry_id)
        return match.group(1) if match else None
