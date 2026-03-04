"""
Pinecone vector database service.
Handles embedding generation (OpenAI) and upsert/query operations.
"""
from __future__ import annotations

import asyncio
import hashlib
from typing import Any, Dict, List, Optional

import structlog
from openai import AsyncOpenAI
from pinecone import Pinecone, ServerlessSpec

from app.config import settings

log = structlog.get_logger()

_openai_client: Optional[AsyncOpenAI] = None
_pinecone_index = None


def _get_openai_client() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


def _get_pinecone_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        existing = [idx.name for idx in pc.list_indexes()]
        if settings.pinecone_index_name not in existing:
            pc.create_index(
                name=settings.pinecone_index_name,
                dimension=settings.pinecone_index_dimension,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        _pinecone_index = pc.Index(settings.pinecone_index_name)
    return _pinecone_index


async def get_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for a list of texts using OpenAI."""
    client = _get_openai_client()
    all_embeddings: List[List[float]] = []

    batch_size = settings.embedding_batch_size
    for i in range(0, len(texts), batch_size):
        batch = texts[i: i + batch_size]
        # Clean texts
        batch = [t.replace("\n", " ").strip() or "empty" for t in batch]
        resp = await client.embeddings.create(
            model=settings.embedding_model,
            input=batch,
        )
        all_embeddings.extend([item.embedding for item in resp.data])

    return all_embeddings


async def upsert_papers(
    papers: List[Dict[str, Any]],
    namespace: str,
) -> None:
    """Embed papers and upsert to Pinecone."""
    if not settings.pinecone_api_key:
        log.warning("Pinecone API key not set – skipping upsert")
        return

    index = _get_pinecone_index()
    texts = [
        f"{p.get('title', '')} {p.get('abstract', '')[:500]}"
        for p in papers
    ]
    embeddings = await get_embeddings(texts)

    vectors = []
    for paper, emb in zip(papers, embeddings):
        paper_id = _paper_id(paper)
        metadata = {
            "title": paper.get("title", ""),
            "authors": ", ".join(paper.get("authors") or [])[:500],
            "year": paper.get("year") or 0,
            "venue": paper.get("venue") or "",
            "doi": paper.get("doi") or "",
            "ieee_number": paper.get("ieee_number") or 0,
            "ieee_citation": (paper.get("ieee_citation") or "")[:1000],
            "summary": (paper.get("summary") or "")[:1000],
        }
        vectors.append({"id": paper_id, "values": emb, "metadata": metadata})

    # Upsert in batches of 100
    for i in range(0, len(vectors), 100):
        index.upsert(vectors=vectors[i: i + 100], namespace=namespace)

    log.info("Pinecone: upserted vectors", count=len(vectors), namespace=namespace)


async def query_papers(
    query_text: str,
    namespace: str,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Query Pinecone for relevant papers given a text query."""
    if not settings.pinecone_api_key:
        log.warning("Pinecone API key not set – returning empty results")
        return []

    index = _get_pinecone_index()
    query_embedding = await get_embeddings([query_text])
    results = index.query(
        vector=query_embedding[0],
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
    )
    return [match.metadata for match in results.matches]


def _paper_id(paper: Dict[str, Any]) -> str:
    """Generate a stable ID for a paper."""
    key = (paper.get("doi") or paper.get("title") or "unknown").encode()
    return hashlib.sha256(key).hexdigest()[:32]
