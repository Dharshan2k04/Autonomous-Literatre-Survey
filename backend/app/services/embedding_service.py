"""Embedding service using OpenAI text-embedding-3-large."""

from __future__ import annotations

import asyncio
from typing import List

import numpy as np

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmbeddingService:
    """Generate embeddings using OpenAI's embedding models."""

    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not settings.has_openai:
                raise RuntimeError("OpenAI API key is required for embeddings")
            from openai import AsyncOpenAI
            self._client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    @property
    def available(self) -> bool:
        return settings.has_openai

    async def embed_text(self, text: str) -> list[float]:
        """Embed a single text string."""
        response = await self.client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text,
            dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
        )
        return response.data[0].embedding

    async def embed_texts(self, texts: list[str], batch_size: int = 50) -> list[list[float]]:
        """Embed multiple texts with batching to respect API limits."""
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            logger.debug("embedding_batch", batch_num=i // batch_size + 1, size=len(batch))

            response = await self.client.embeddings.create(
                model=settings.OPENAI_EMBEDDING_MODEL,
                input=batch,
                dimensions=settings.OPENAI_EMBEDDING_DIMENSIONS,
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

            # Small delay between batches to avoid rate limiting
            if i + batch_size < len(texts):
                await asyncio.sleep(0.2)

        return all_embeddings

    async def embed_paper(self, title: str, abstract: str | None = None) -> list[float]:
        """Create a combined embedding for a paper (title + abstract)."""
        text = title
        if abstract:
            text = f"{title}\n\n{abstract}"
        return await self.embed_text(text)

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two embedding vectors."""
        a_arr = np.array(a)
        b_arr = np.array(b)
        return float(np.dot(a_arr, b_arr) / (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)))
