"""
Survey Architect Agent
Clusters papers into taxonomies using embedding similarity,
identifies research gaps via LLM synthesis, and compiles a
structured markdown survey with bibliography.
"""
from __future__ import annotations

import json
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import settings
from app.services.pinecone_service import get_embeddings

log = structlog.get_logger()

GAP_SYSTEM = """You are an expert academic researcher tasked with identifying research gaps.
Given a set of paper summaries clustered by topic, analyze the collection and identify:
1. Under-explored research directions
2. Methodological limitations in current work
3. Open problems not addressed by existing papers
4. Promising future directions

Return a JSON array of 5-8 research gap strings. Each string should be a concise, specific
research gap statement (1-2 sentences). Return ONLY the JSON array."""

SURVEY_SYSTEM = """You are an expert academic writer. Create a structured literature survey
in markdown format. The survey should include:
1. Introduction (overview of the research area)
2. Taxonomy (describe the clusters and how they relate)
3. Analysis per cluster (key contributions, trends, limitations)
4. Research Gaps (from the provided gap analysis)
5. Conclusion

Use IEEE citation numbers [n] when referencing papers. Be technical and precise."""


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_arr = np.array(a)
    b_arr = np.array(b)
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)


def _cluster_papers(
    papers: List[Dict[str, Any]],
    embeddings: List[List[float]],
    threshold: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Simple greedy clustering: assign each paper to an existing cluster centroid
    if similarity > threshold, otherwise create a new cluster.
    """
    if threshold is None:
        threshold = settings.clustering_similarity_threshold
    if not embeddings:
        return papers

    clusters: List[Dict[str, Any]] = []
    cluster_centroids: List[List[float]] = []

    for i, (paper, emb) in enumerate(zip(papers, embeddings)):
        assigned = False
        best_sim = -1.0
        best_cluster = -1
        for c_idx, centroid in enumerate(cluster_centroids):
            sim = _cosine_similarity(emb, centroid)
            if sim > best_sim:
                best_sim = sim
                best_cluster = c_idx
        if best_sim >= threshold and best_cluster >= 0:
            clusters[best_cluster]["members"].append(paper)
            # Update centroid (running average)
            n = len(clusters[best_cluster]["members"])
            centroid = cluster_centroids[best_cluster]
            cluster_centroids[best_cluster] = [
                (centroid[k] * (n - 1) + emb[k]) / n
                for k in range(len(emb))
            ]
            assigned = True

        if not assigned:
            # Derive a label from the first paper's title (first 5 words)
            words = paper.get("title", "Cluster").split()[:5]
            label = " ".join(words)
            clusters.append({"label": label, "members": [paper]})
            cluster_centroids.append(emb)

    # Assign cluster labels back to papers
    result = []
    for cluster in clusters:
        for paper in cluster["members"]:
            result.append({**paper, "cluster_label": cluster["label"]})

    return result


async def _identify_research_gaps(
    papers: List[Dict[str, Any]],
    topic: str,
    llm: ChatOpenAI,
) -> List[str]:
    """Use LLM to identify research gaps from paper summaries."""
    summaries = []
    for p in papers[:30]:  # Use top 30 papers
        summaries.append(
            f"[{p.get('ieee_number')}] {p.get('title', '')}: {p.get('summary', '')}"
        )
    content = f"Research topic: {topic}\n\nPaper summaries:\n" + "\n".join(summaries)
    response = await llm.ainvoke([
        SystemMessage(content=GAP_SYSTEM),
        HumanMessage(content=content),
    ])
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    gaps = json.loads(raw.strip())
    return gaps


def _compile_markdown(
    topic: str,
    papers: List[Dict[str, Any]],
    gaps: List[str],
    survey_text: str,
) -> str:
    """Assemble the final markdown survey."""
    lines = [f"# Literature Survey: {topic}\n"]
    lines.append(survey_text)
    lines.append("\n---\n## Bibliography\n")
    for paper in sorted(papers, key=lambda p: p.get("ieee_number") or 999):
        lines.append(paper.get("ieee_citation", ""))
    return "\n".join(lines)


async def run_survey_architect(
    papers: List[Dict[str, Any]],
    topic: str,
    namespace: str,
) -> Tuple[List[Dict[str, Any]], List[str], str]:
    """
    Run Survey Architect Agent.
    Returns: (papers_with_clusters, research_gaps, survey_markdown)
    """
    log.info("SurveyArchitect: starting", papers=len(papers))
    llm = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.4,
    )

    # ------------------------------------------------------------------
    # 1. Get embeddings from Pinecone service (cached from upsert step)
    # ------------------------------------------------------------------
    texts = [
        f"{p.get('title', '')} {p.get('abstract', '')[:300]}"
        for p in papers
    ]
    embeddings = await get_embeddings(texts)

    # ------------------------------------------------------------------
    # 2. Cluster
    # ------------------------------------------------------------------
    clustered_papers = _cluster_papers(papers, embeddings)
    log.info("SurveyArchitect: clustering done")

    # ------------------------------------------------------------------
    # 3. Research gaps
    # ------------------------------------------------------------------
    gaps = await _identify_research_gaps(clustered_papers, topic, llm)
    log.info("SurveyArchitect: gaps identified", gaps=len(gaps))

    # ------------------------------------------------------------------
    # 4. Compile survey text via LLM
    # ------------------------------------------------------------------
    cluster_overview = defaultdict(list)
    for p in clustered_papers:
        cluster_overview[p.get("cluster_label", "General")].append(
            f"  - [{p.get('ieee_number')}] {p.get('title', '')}"
        )

    cluster_text = "\n".join(
        f"**{label}**:\n" + "\n".join(items)
        for label, items in cluster_overview.items()
    )

    gaps_text = "\n".join(f"- {g}" for g in gaps)
    summaries_text = "\n".join(
        f"[{p.get('ieee_number')}] {p.get('title', '')}: {p.get('summary', '')}"
        for p in clustered_papers[:20]
    )

    prompt = (
        f"Research topic: {topic}\n\n"
        f"Paper clusters:\n{cluster_text}\n\n"
        f"Key paper summaries:\n{summaries_text}\n\n"
        f"Identified research gaps:\n{gaps_text}\n\n"
        "Write the complete structured literature survey in markdown."
    )

    survey_resp = await llm.ainvoke([
        SystemMessage(content=SURVEY_SYSTEM),
        HumanMessage(content=prompt),
    ])
    survey_text = survey_resp.content.strip()

    # ------------------------------------------------------------------
    # 5. Assemble final markdown
    # ------------------------------------------------------------------
    survey_markdown = _compile_markdown(topic, clustered_papers, gaps, survey_text)
    log.info("SurveyArchitect: survey compiled")

    return clustered_papers, gaps, survey_markdown
