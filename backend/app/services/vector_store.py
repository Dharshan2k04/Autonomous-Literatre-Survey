"""Pinecone vector store service with namespace isolation."""

from __future__ import annotations

from typing import Any

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class VectorStoreService:
    """Pinecone vector store with survey-specific namespaces."""

    def __init__(self):
        self._index = None

    @property
    def available(self) -> bool:
        return settings.has_pinecone

    @property
    def index(self):
        if self._index is None:
            if not settings.has_pinecone:
                raise RuntimeError("Pinecone API key is required")
            from pinecone import Pinecone
            pc = Pinecone(api_key=settings.PINECONE_API_KEY)

            # Create index if it doesn't exist
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            if settings.PINECONE_INDEX_NAME not in existing_indexes:
                from pinecone import ServerlessSpec
                pc.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=settings.OPENAI_EMBEDDING_DIMENSIONS,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region=settings.PINECONE_ENVIRONMENT),
                )
                logger.info("pinecone_index_created", index=settings.PINECONE_INDEX_NAME)

            self._index = pc.Index(settings.PINECONE_INDEX_NAME)
        return self._index

    async def upsert_papers(
        self,
        namespace: str,
        paper_ids: list[str],
        embeddings: list[list[float]],
        metadata_list: list[dict[str, Any]],
    ) -> int:
        """Upsert paper embeddings into Pinecone with the given namespace."""
        vectors = []
        for pid, emb, meta in zip(paper_ids, embeddings, metadata_list):
            # Pinecone metadata values must be strings, numbers, booleans, or lists of strings
            clean_meta = {}
            for k, v in meta.items():
                if isinstance(v, (str, int, float, bool)):
                    clean_meta[k] = v
                elif isinstance(v, list) and all(isinstance(i, str) for i in v):
                    clean_meta[k] = v
                elif v is not None:
                    clean_meta[k] = str(v)
            vectors.append({"id": pid, "values": emb, "metadata": clean_meta})

        # Batch upsert (Pinecone recommends max 100 per call)
        batch_size = 100
        total_upserted = 0
        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            self.index.upsert(vectors=batch, namespace=namespace)
            total_upserted += len(batch)

        logger.info("pinecone_upserted", namespace=namespace, count=total_upserted)
        return total_upserted

    async def query(
        self,
        namespace: str,
        query_embedding: list[float],
        top_k: int = 10,
        filter_dict: dict | None = None,
    ) -> list[dict[str, Any]]:
        """Query the vector store for similar papers."""
        kwargs = {
            "vector": query_embedding,
            "top_k": top_k,
            "namespace": namespace,
            "include_metadata": True,
        }
        if filter_dict:
            kwargs["filter"] = filter_dict

        results = self.index.query(**kwargs)

        return [
            {
                "id": match.id,
                "score": match.score,
                "metadata": match.metadata or {},
            }
            for match in results.matches
        ]

    async def delete_namespace(self, namespace: str) -> None:
        """Delete all vectors in a namespace."""
        try:
            self.index.delete(delete_all=True, namespace=namespace)
            logger.info("pinecone_namespace_deleted", namespace=namespace)
        except Exception as e:
            logger.warning("pinecone_delete_error", namespace=namespace, error=str(e))

    async def get_namespace_stats(self, namespace: str) -> dict:
        """Get stats for a namespace."""
        stats = self.index.describe_index_stats()
        ns_stats = stats.get("namespaces", {}).get(namespace, {})
        return {"vector_count": ns_stats.get("vector_count", 0)}
