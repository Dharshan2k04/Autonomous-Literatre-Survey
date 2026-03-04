"""Agent 4: Survey Architect — Clusters papers, identifies gaps, generates survey."""

from __future__ import annotations

import json
from typing import Any

import numpy as np

from app.core.logging import get_logger
from app.services.llm_service import BaseLLMService

logger = get_logger(__name__)

TAXONOMY_SYSTEM_PROMPT = """You are an expert academic survey writer. Given a set of papers with their 
embeddings clustered into groups, create a taxonomy and identify research gaps.

Respond with ONLY valid JSON:
{
    "taxonomy": {
        "categories": [
            {
                "id": 0,
                "name": "Category Name",
                "description": "Brief description of this research category",
                "paper_numbers": [1, 3, 5]
            }
        ]
    },
    "research_gaps": [
        "Description of identified research gap 1",
        "Description of identified research gap 2"
    ],
    "key_trends": [
        "Description of key trend 1"
    ]
}"""

SURVEY_SYSTEM_PROMPT = """You are an expert academic survey writer. Generate a comprehensive, 
publication-ready literature survey in markdown format.

The survey should include:
1. **Title** — descriptive title for the survey
2. **Abstract** — 150-200 word summary
3. **I. Introduction** — motivation, scope, and contributions
4. **II. Background** — key concepts and definitions
5. **III-N. Thematic Sections** — one section per taxonomy category, discussing papers with IEEE citation numbers [N]
6. **N+1. Research Gaps and Future Directions** — identified gaps and opportunities
7. **N+2. Conclusion** — summary of findings
8. **References** — numbered bibliography in IEEE format

IMPORTANT:
- Cite papers using their IEEE numbers like [1], [2], [3-5]
- Use formal academic writing style
- Draw connections between papers in the same category
- Highlight contrasts and complementary approaches
- Each thematic section should synthesize, not just list papers"""


class SurveyArchitectAgent:
    """Clusters papers into taxonomies, identifies gaps, and generates surveys."""

    def __init__(self, llm: BaseLLMService):
        self.llm = llm

    async def cluster_papers(
        self,
        papers: list[dict[str, Any]],
        embeddings: list[list[float]],
        num_clusters: int | None = None,
    ) -> list[dict[str, Any]]:
        """Cluster papers using embedding similarity (k-means).

        Returns papers with cluster_id assigned.
        """
        if len(papers) < 3:
            # Not enough papers to cluster meaningfully
            for paper in papers:
                paper["cluster_id"] = 0
            return papers

        # Determine number of clusters
        if num_clusters is None:
            num_clusters = min(max(3, len(papers) // 5), 8)

        embeddings_arr = np.array(embeddings)

        # Simple k-means implementation (avoid sklearn dependency)
        cluster_ids = self._kmeans(embeddings_arr, num_clusters, max_iter=50)

        for paper, cid in zip(papers, cluster_ids):
            paper["cluster_id"] = int(cid)

        logger.info("papers_clustered", num_papers=len(papers), num_clusters=num_clusters)
        return papers

    async def generate_taxonomy(
        self,
        papers: list[dict[str, Any]],
        topic: str,
    ) -> dict[str, Any]:
        """Generate a taxonomy and identify research gaps using LLM."""
        logger.info("taxonomy_generation_start", paper_count=len(papers))

        # Group papers by cluster
        clusters: dict[int, list] = {}
        for paper in papers:
            cid = paper.get("cluster_id", 0)
            if cid not in clusters:
                clusters[cid] = []
            clusters[cid].append({
                "ieee_number": paper.get("ieee_number"),
                "title": paper.get("title"),
                "year": paper.get("year"),
                "summary": paper.get("summary", ""),
            })

        prompt = f"""Research Topic: {topic}

Paper clusters:
{json.dumps(clusters, indent=2)}

Total papers: {len(papers)}

Analyze these paper clusters and:
1. Name each cluster category with a descriptive academic name
2. Identify research gaps
3. Note key trends in the field"""

        try:
            response = await self.llm.generate_structured(
                prompt=prompt,
                system_prompt=TAXONOMY_SYSTEM_PROMPT,
                temperature=0.4,
            )
            result = json.loads(response)
            logger.info("taxonomy_generated", categories=len(result.get("taxonomy", {}).get("categories", [])))
            return result
        except Exception as e:
            logger.error("taxonomy_generation_error", error=str(e))
            return self._fallback_taxonomy(clusters)

    async def generate_survey(
        self,
        topic: str,
        papers: list[dict[str, Any]],
        taxonomy: dict[str, Any],
        citations: list[dict[str, Any]],
    ) -> str:
        """Generate the final markdown survey document.

        Args:
            topic: Research topic.
            papers: Papers with cluster assignments.
            taxonomy: Taxonomy with categories and gaps.
            citations: IEEE-formatted citations.

        Returns:
            Complete survey in markdown format.
        """
        logger.info("survey_generation_start", topic=topic)

        # Build the bibliography
        bibliography = "\n".join(c.get("ieee_citation", "") for c in citations)

        # Build paper summaries grouped by category
        categories = taxonomy.get("taxonomy", {}).get("categories", [])
        category_summaries = {}
        for cat in categories:
            cat_papers = []
            for pnum in cat.get("paper_numbers", []):
                # Find the matching paper and citation
                matching_citation = next(
                    (c for c in citations if c.get("ieee_number") == pnum), None
                )
                matching_paper = next(
                    (p for p in papers if p.get("ieee_number") == pnum), None
                )
                if matching_citation:
                    cat_papers.append({
                        "ieee_number": pnum,
                        "title": matching_paper.get("title", "") if matching_paper else "",
                        "summary": matching_citation.get("summary", ""),
                        "year": matching_paper.get("year") if matching_paper else None,
                    })
            category_summaries[cat["name"]] = {
                "description": cat.get("description", ""),
                "papers": cat_papers,
            }

        research_gaps = taxonomy.get("research_gaps", [])
        key_trends = taxonomy.get("key_trends", [])

        prompt = f"""Research Topic: {topic}

Taxonomy Categories and Papers:
{json.dumps(category_summaries, indent=2)}

Research Gaps:
{json.dumps(research_gaps, indent=2)}

Key Trends:
{json.dumps(key_trends, indent=2)}

Bibliography:
{bibliography}

Total papers surveyed: {len(papers)}

Generate a comprehensive academic literature survey in markdown format.
Use IEEE citation numbers [N] when referencing papers.
Make it publication-ready with proper academic writing."""

        try:
            survey = await self.llm.generate(
                prompt=prompt,
                system_prompt=SURVEY_SYSTEM_PROMPT,
                temperature=0.5,
                max_tokens=8000,
            )
            logger.info("survey_generated", length=len(survey))
            return survey
        except Exception as e:
            logger.error("survey_generation_error", error=str(e))
            return self._fallback_survey(topic, citations, categories)

    def _kmeans(self, data: np.ndarray, k: int, max_iter: int = 50) -> list[int]:
        """Simple k-means clustering implementation."""
        n = data.shape[0]
        if n <= k:
            return list(range(n))

        # Initialize centroids randomly
        rng = np.random.default_rng(42)
        indices = rng.choice(n, size=k, replace=False)
        centroids = data[indices].copy()

        labels = np.zeros(n, dtype=int)
        for _ in range(max_iter):
            # Assign points to nearest centroid
            distances = np.linalg.norm(data[:, np.newaxis] - centroids[np.newaxis], axis=2)
            new_labels = np.argmin(distances, axis=1)

            if np.array_equal(labels, new_labels):
                break
            labels = new_labels

            # Update centroids
            for j in range(k):
                mask = labels == j
                if mask.sum() > 0:
                    centroids[j] = data[mask].mean(axis=0)

        return labels.tolist()

    def _fallback_taxonomy(self, clusters: dict) -> dict:
        """Generate a basic taxonomy without LLM."""
        categories = []
        for cid, papers in clusters.items():
            categories.append({
                "id": cid,
                "name": f"Research Area {cid + 1}",
                "description": f"A cluster of {len(papers)} related papers",
                "paper_numbers": [p.get("ieee_number") for p in papers if p.get("ieee_number")],
            })
        return {
            "taxonomy": {"categories": categories},
            "research_gaps": ["Further analysis needed with LLM service configured"],
            "key_trends": [],
        }

    def _fallback_survey(
        self, topic: str, citations: list[dict], categories: list[dict]
    ) -> str:
        """Generate a basic survey structure without LLM."""
        sections = [f"# Literature Survey: {topic}\n"]
        sections.append("## Abstract\n")
        sections.append(f"This survey reviews {len(citations)} papers on the topic of {topic}.\n")
        sections.append("## I. Introduction\n")
        sections.append(f"This document provides a systematic literature review of {topic}.\n")

        for cat in categories:
            sections.append(f"## {cat.get('name', 'Section')}\n")
            sections.append(f"{cat.get('description', '')}\n")
            for pnum in cat.get("paper_numbers", []):
                matching = next((c for c in citations if c.get("ieee_number") == pnum), None)
                if matching:
                    sections.append(f"- [{pnum}] {matching.get('summary', '')}\n")

        sections.append("## References\n")
        for c in citations:
            sections.append(f"{c.get('ieee_citation', '')}\n")

        return "\n".join(sections)
