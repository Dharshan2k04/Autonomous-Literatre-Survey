"""Agent 3: IEEE Formatter — Generates IEEE citations and contextual summaries."""

from __future__ import annotations

import json
from typing import Any

from app.core.logging import get_logger
from app.schemas.paper import PaperSearchResult
from app.services.llm_service import BaseLLMService

logger = get_logger(__name__)

IEEE_SYSTEM_PROMPT = """You are an expert academic citation formatter specializing in IEEE citation style.

For each paper, generate:
1. A properly formatted IEEE citation following these rules:
   - Authors: First initial(s). Last name (e.g., "A. B. Smith")
   - For 1-6 authors, list all; for 7+, list first author et al.
   - Title in quotation marks
   - Journal/Conference in italics (use * for markdown italic)
   - Volume, number, pages, year
   - DOI if available
   
2. A contextual summary (2-3 sentences) that explains the paper's contribution 
   to the research topic through comparative analysis with related works.

Respond ONLY with valid JSON in this format:
{
    "citations": [
        {
            "ieee_number": 1,
            "ieee_citation": "[1] A. Smith and B. Jones, \"Paper Title,\" *Journal Name*, vol. X, no. Y, pp. 1-10, 2024.",
            "summary": "This paper introduces... It extends prior work by... The proposed approach achieves..."
        },
        ...
    ]
}"""


class IEEEFormatterAgent:
    """Generates IEEE-formatted citations and contextual summaries."""

    def __init__(self, llm: BaseLLMService):
        self.llm = llm

    async def format_papers(
        self,
        papers: list[PaperSearchResult],
        topic: str,
        batch_size: int = 10,
    ) -> list[dict[str, Any]]:
        """Generate IEEE citations and summaries for all papers.

        Args:
            papers: List of paper search results.
            topic: The research topic for contextual summaries.
            batch_size: Papers per LLM call (to manage token limits).

        Returns:
            List of dicts with ieee_number, ieee_citation, and summary.
        """
        logger.info("ieee_formatter_start", paper_count=len(papers))

        all_citations = []
        current_number = 1

        for i in range(0, len(papers), batch_size):
            batch = papers[i : i + batch_size]
            batch_citations = await self._format_batch(batch, topic, current_number)
            all_citations.extend(batch_citations)
            current_number += len(batch_citations)

        logger.info("ieee_formatter_complete", citation_count=len(all_citations))
        return all_citations

    async def _format_batch(
        self,
        papers: list[PaperSearchResult],
        topic: str,
        start_number: int,
    ) -> list[dict[str, Any]]:
        """Format a batch of papers."""
        # Build paper info for the prompt
        papers_info = []
        for idx, paper in enumerate(papers):
            info = {
                "number": start_number + idx,
                "title": paper.title,
                "authors": paper.authors[:10],  # Limit authors for token efficiency
                "year": paper.year,
                "venue": paper.venue,
                "doi": paper.doi,
                "abstract": (paper.abstract[:500] if paper.abstract else "No abstract available"),
                "citation_count": paper.citation_count,
            }
            papers_info.append(info)

        prompt = f"""Research Topic: {topic}

Papers to format (starting at [{start_number}]):

{json.dumps(papers_info, indent=2)}

Generate IEEE citations and contextual summaries for each paper.
Make summaries relate to the research topic "{topic}"."""

        try:
            response = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt=IEEE_SYSTEM_PROMPT,
                temperature=0.3,
            )
            result = json.loads(response)
            return result.get("citations", [])

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("ieee_format_llm_error", error=str(e))
            # Fallback: generate basic citations programmatically
            return [self._fallback_citation(paper, start_number + idx) 
                    for idx, paper in enumerate(papers)]

    def _fallback_citation(self, paper: PaperSearchResult, number: int) -> dict[str, Any]:
        """Generate a basic IEEE citation without LLM."""
        # Format authors
        if paper.authors:
            if len(paper.authors) <= 6:
                formatted_authors = self._format_author_list(paper.authors)
            else:
                formatted_authors = self._format_author_name(paper.authors[0]) + " et al."
        else:
            formatted_authors = "Unknown"

        # Build citation
        parts = [f"[{number}] {formatted_authors}"]
        parts.append(f'"{paper.title},"')
        if paper.venue:
            parts.append(f"*{paper.venue}*,")
        if paper.year:
            parts.append(f"{paper.year}.")
        if paper.doi:
            parts.append(f"doi: {paper.doi}.")

        citation = " ".join(parts)
        summary = f"This paper addresses {paper.title.lower()}."
        if paper.abstract:
            summary = paper.abstract[:200] + "..."

        return {
            "ieee_number": number,
            "ieee_citation": citation,
            "summary": summary,
        }

    @staticmethod
    def _format_author_name(name: str) -> str:
        """Format a single author name to IEEE style: 'First Last' -> 'F. Last'."""
        parts = name.strip().split()
        if len(parts) >= 2:
            initials = ". ".join(p[0].upper() for p in parts[:-1])
            return f"{initials}. {parts[-1]}"
        return name

    def _format_author_list(self, authors: list[str]) -> str:
        """Format a list of authors to IEEE style."""
        formatted = [self._format_author_name(a) for a in authors]
        if len(formatted) == 1:
            return formatted[0]
        elif len(formatted) == 2:
            return f"{formatted[0]} and {formatted[1]}"
        else:
            return ", ".join(formatted[:-1]) + ", and " + formatted[-1]
