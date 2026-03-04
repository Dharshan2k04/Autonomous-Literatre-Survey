"""
IEEE Formatter Agent
Generates publication-ready IEEE citations and contextual 2-3 sentence
summaries for each paper using GPT-4.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings

log = structlog.get_logger()

CITATION_SYSTEM = """You are an IEEE citation formatting expert. Format the given paper metadata
into a proper IEEE reference. Follow these rules:
- Authors: Last name, First initial. (e.g., "J. Smith, A. Jones")
- Up to 3 authors listed; if more, use "et al." after the third
- Title in quotes
- Journal/Conference in italics notation: *Venue*
- Volume, number, pages, year as available
- Include DOI if available as: doi: XX.XXXX/XXXXXX

Return ONLY the formatted citation string, nothing else."""

SUMMARY_SYSTEM = """You are an academic research analyst. Write a concise 2-3 sentence summary
of the paper's contribution to the given research topic. The summary should:
1. State the paper's core contribution or finding
2. Explain its relevance to the research topic
3. Optionally compare or contrast with related work

Return ONLY the summary paragraph, no headings or extra text."""


async def _format_single_paper(
    paper: Dict[str, Any],
    topic: str,
    ieee_number: int,
    llm: ChatOpenAI,
) -> Dict[str, Any]:
    """Format one paper: generate IEEE citation + summary concurrently."""

    def _author_list(authors: List[str]) -> str:
        if not authors:
            return "Unknown Author"
        if len(authors) <= 3:
            return ", ".join(authors)
        return ", ".join(authors[:3]) + " et al."

    metadata = (
        f"Title: {paper.get('title', 'Unknown')}\n"
        f"Authors: {_author_list(paper.get('authors') or [])}\n"
        f"Year: {paper.get('year', 'n.d.')}\n"
        f"Venue: {paper.get('venue') or 'arXiv preprint'}\n"
        f"DOI: {paper.get('doi') or 'N/A'}\n"
        f"Abstract: {(paper.get('abstract') or '')[:600]}"
    )

    citation_task = asyncio.create_task(
        llm.ainvoke([
            SystemMessage(content=CITATION_SYSTEM),
            HumanMessage(content=metadata),
        ])
    )
    summary_task = asyncio.create_task(
        llm.ainvoke([
            SystemMessage(content=SUMMARY_SYSTEM),
            HumanMessage(
                content=f"Research topic: {topic}\n\nPaper metadata:\n{metadata}"
            ),
        ])
    )

    citation_resp, summary_resp = await asyncio.gather(citation_task, summary_task)

    return {
        **paper,
        "ieee_citation": f"[{ieee_number}] {citation_resp.content.strip()}",
        "ieee_number": ieee_number,
        "summary": summary_resp.content.strip(),
    }


async def run_ieee_formatter(
    papers: List[Dict[str, Any]],
    topic: str,
) -> List[Dict[str, Any]]:
    """Run IEEE Formatter Agent over all papers concurrently."""
    log.info("IEEEFormatter: formatting papers", count=len(papers))
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.1,
    )

    # Process in batches of 10 to avoid rate-limiting
    batch_size = 10
    formatted: List[Dict[str, Any]] = []

    for i in range(0, len(papers), batch_size):
        batch = papers[i: i + batch_size]
        tasks = [
            _format_single_paper(p, topic, i + j + 1, llm)
            for j, p in enumerate(batch)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for j, res in enumerate(results):
            if isinstance(res, Exception):
                log.warning("IEEEFormatter: paper formatting failed", error=str(res))
                paper = batch[j]
                formatted.append({
                    **paper,
                    "ieee_citation": f"[{i + j + 1}] {paper.get('title', 'Unknown title')}.",
                    "ieee_number": i + j + 1,
                    "summary": "Summary unavailable.",
                })
            else:
                formatted.append(res)

    log.info("IEEEFormatter: done", formatted=len(formatted))
    return formatted
