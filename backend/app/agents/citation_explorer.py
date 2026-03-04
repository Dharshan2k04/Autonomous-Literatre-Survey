"""
Citation Explorer Agent
Executes parallel API calls to Semantic Scholar, arXiv, and Crossref,
deduplicates by DOI/title similarity, ranks by citation count and recency,
and returns up to 50 papers.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
import structlog
from rapidfuzz import fuzz

from app.config import settings

log = structlog.get_logger()

# ---------------------------------------------------------------------------
# Data class for a normalised paper
# ---------------------------------------------------------------------------

def _make_paper(
    title: str,
    authors: List[str],
    year: Optional[int],
    venue: Optional[str],
    doi: Optional[str],
    arxiv_id: Optional[str],
    url: Optional[str],
    abstract: Optional[str],
    citation_count: int,
    source: str,
) -> Dict[str, Any]:
    return {
        "title": title,
        "authors": authors,
        "year": year,
        "venue": venue,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "url": url,
        "abstract": abstract,
        "citation_count": citation_count,
        "source": source,
    }


# ---------------------------------------------------------------------------
# Source-specific fetchers
# ---------------------------------------------------------------------------

async def _fetch_semantic_scholar(query: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch papers from Semantic Scholar API."""
    params = {
        "query": query,
        "limit": settings.semantic_scholar_max_results,
        "fields": "title,authors,year,venue,externalIds,abstract,citationCount,url",
    }
    headers = {}
    if settings.semantic_scholar_api_key:
        headers["x-api-key"] = settings.semantic_scholar_api_key

    try:
        resp = await client.get(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params=params,
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        papers = []
        for p in data.get("data", []):
            ext_ids = p.get("externalIds") or {}
            papers.append(
                _make_paper(
                    title=p.get("title", ""),
                    authors=[a["name"] for a in (p.get("authors") or [])],
                    year=p.get("year"),
                    venue=p.get("venue"),
                    doi=ext_ids.get("DOI"),
                    arxiv_id=ext_ids.get("ArXiv"),
                    url=p.get("url"),
                    abstract=p.get("abstract"),
                    citation_count=p.get("citationCount") or 0,
                    source="semantic_scholar",
                )
            )
        return papers
    except Exception as exc:
        log.warning("SemanticScholar fetch failed", error=str(exc))
        return []


async def _fetch_arxiv(query: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch papers from arXiv API."""
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": settings.arxiv_max_results,
    }
    try:
        resp = await client.get(
            "http://export.arxiv.org/api/query",
            params=params,
            timeout=20,
        )
        resp.raise_for_status()
        import xml.etree.ElementTree as ET
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        root = ET.fromstring(resp.text)
        papers = []
        for entry in root.findall("atom:entry", ns):
            title = (entry.findtext("atom:title", namespaces=ns) or "").strip().replace("\n", " ")
            abstract = (entry.findtext("atom:summary", namespaces=ns) or "").strip()
            published = entry.findtext("atom:published", namespaces=ns) or ""
            year = int(published[:4]) if published else None
            link_el = entry.find("atom:id", ns)
            arxiv_url = link_el.text.strip() if link_el is not None else None
            arxiv_id = arxiv_url.split("/abs/")[-1] if arxiv_url else None
            authors = [
                a.findtext("atom:name", namespaces=ns) or ""
                for a in entry.findall("atom:author", ns)
            ]
            # arXiv DOI link
            doi = None
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "doi":
                    doi = link.attrib.get("href", "").replace("http://dx.doi.org/", "")
            papers.append(
                _make_paper(
                    title=title,
                    authors=authors,
                    year=year,
                    venue="arXiv",
                    doi=doi,
                    arxiv_id=arxiv_id,
                    url=arxiv_url,
                    abstract=abstract,
                    citation_count=0,
                    source="arxiv",
                )
            )
        return papers
    except Exception as exc:
        log.warning("arXiv fetch failed", error=str(exc))
        return []


async def _fetch_crossref(query: str, client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    """Fetch papers from Crossref API."""
    params = {
        "query": query,
        "rows": settings.crossref_max_results,
        "select": "title,author,published-print,container-title,DOI,abstract,is-referenced-by-count,URL",
    }
    try:
        resp = await client.get(
            "https://api.crossref.org/works",
            params=params,
            timeout=20,
            headers={"User-Agent": "AutonomousLiteratureSurvey/1.0 (mailto:admin@example.com)"},
        )
        resp.raise_for_status()
        items = resp.json().get("message", {}).get("items", [])
        papers = []
        for item in items:
            titles = item.get("title") or []
            title = titles[0] if titles else ""
            authors = []
            for a in item.get("author") or []:
                given = a.get("given", "")
                family = a.get("family", "")
                authors.append(f"{given} {family}".strip())
            year = None
            pub = item.get("published-print") or item.get("published-online") or {}
            date_parts = pub.get("date-parts", [[]])
            if date_parts and date_parts[0]:
                year = date_parts[0][0]
            venue_list = item.get("container-title") or []
            venue = venue_list[0] if venue_list else None
            doi = item.get("DOI")
            abstract = item.get("abstract", "")
            # Strip JATS tags from Crossref abstracts
            if abstract:
                import re
                abstract = re.sub(r"<[^>]+>", "", abstract).strip()
            papers.append(
                _make_paper(
                    title=title,
                    authors=authors,
                    year=year,
                    venue=venue,
                    doi=doi,
                    arxiv_id=None,
                    url=item.get("URL"),
                    abstract=abstract,
                    citation_count=item.get("is-referenced-by-count") or 0,
                    source="crossref",
                )
            )
        return papers
    except Exception as exc:
        log.warning("Crossref fetch failed", error=str(exc))
        return []


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _deduplicate(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove near-duplicate papers by DOI and title similarity."""
    seen_dois: set = set()
    unique: List[Dict[str, Any]] = []

    for paper in papers:
        # DOI-based dedup
        doi = (paper.get("doi") or "").strip().lower()
        if doi and doi in seen_dois:
            continue
        # Title fuzzy dedup
        title = paper.get("title", "").lower().strip()
        is_dup = False
        for existing in unique:
            existing_title = existing.get("title", "").lower().strip()
            if fuzz.ratio(title, existing_title) > 92:
                # Keep the one with higher citation count
                if paper["citation_count"] > existing["citation_count"]:
                    unique.remove(existing)
                    if doi:
                        seen_dois.add(doi)
                    unique.append(paper)
                is_dup = True
                break
        if not is_dup:
            if doi:
                seen_dois.add(doi)
            unique.append(paper)

    return unique


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------

def _rank_papers(papers: List[Dict[str, Any]], max_papers: int = 50) -> List[Dict[str, Any]]:
    """Score papers by citation count and recency, return top N."""
    current_year = datetime.now().year

    def score(p: Dict[str, Any]) -> float:
        cite_score = min(p["citation_count"] / 100.0, 10.0)
        year = p.get("year") or (current_year - 10)
        recency_score = max(0, 10 - (current_year - year))
        return cite_score + recency_score

    ranked = sorted(papers, key=score, reverse=True)
    return ranked[:max_papers]


# ---------------------------------------------------------------------------
# Main entry-point
# ---------------------------------------------------------------------------

async def run_citation_explorer(
    sub_queries: List[str],
) -> List[Dict[str, Any]]:
    """Run Citation Explorer Agent – fetch, dedup, rank papers."""
    log.info("CitationExplorer: starting", num_queries=len(sub_queries))

    async with httpx.AsyncClient() as client:
        # Fan out: 3 sources × N queries concurrently
        tasks = []
        for query in sub_queries:
            tasks.append(_fetch_semantic_scholar(query, client))
            tasks.append(_fetch_arxiv(query, client))
            tasks.append(_fetch_crossref(query, client))

        results = await asyncio.gather(*tasks)

    # Flatten
    all_papers: List[Dict[str, Any]] = []
    for batch in results:
        all_papers.extend(batch)

    log.info("CitationExplorer: raw results", total=len(all_papers))

    unique = _deduplicate(all_papers)
    log.info("CitationExplorer: after dedup", unique=len(unique))

    ranked = _rank_papers(unique, settings.max_papers_per_survey)
    log.info("CitationExplorer: final papers", final=len(ranked))

    return ranked
