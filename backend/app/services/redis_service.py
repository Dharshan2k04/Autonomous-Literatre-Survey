"""
Redis caching service for session management and result caching.
"""
from __future__ import annotations

import json
from typing import Any, Optional

import structlog
import redis.asyncio as aioredis

from app.config import settings

log = structlog.get_logger()

_redis_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    """Store JSON-serialisable value in Redis with TTL (seconds)."""
    try:
        r = get_redis()
        await r.setex(key, ttl, json.dumps(value))
    except Exception as exc:
        log.warning("Redis cache_set failed", key=key, error=str(exc))


async def cache_get(key: str) -> Optional[Any]:
    """Retrieve and deserialise a value from Redis."""
    try:
        r = get_redis()
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        log.warning("Redis cache_get failed", key=key, error=str(exc))
        return None


async def cache_delete(key: str) -> None:
    try:
        r = get_redis()
        await r.delete(key)
    except Exception as exc:
        log.warning("Redis cache_delete failed", key=key, error=str(exc))
