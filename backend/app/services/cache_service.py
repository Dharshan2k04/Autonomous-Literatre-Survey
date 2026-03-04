"""Redis cache service for caching and session management."""

from __future__ import annotations

import json
from typing import Any

from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


class CacheService:
    """Redis-based caching with graceful degradation."""

    def __init__(self):
        self._redis = None
        self._available = None

    @property
    async def redis(self):
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                )
                await self._redis.ping()
                self._available = True
                logger.info("redis_connected")
            except Exception as e:
                logger.warning("redis_connection_failed", error=str(e))
                self._available = False
                self._redis = None
        return self._redis

    @property
    def available(self) -> bool:
        return self._available is True

    async def get(self, key: str) -> Any | None:
        """Get a cached value."""
        try:
            client = await self.redis
            if client is None:
                return None
            value = await client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.warning("cache_get_error", key=key, error=str(e))
            return None

    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """Set a cached value with TTL in seconds."""
        try:
            client = await self.redis
            if client is None:
                return False
            await client.setex(key, ttl, json.dumps(value, default=str))
            return True
        except Exception as e:
            logger.warning("cache_set_error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """Delete a cached value."""
        try:
            client = await self.redis
            if client is None:
                return False
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning("cache_delete_error", key=key, error=str(e))
            return False

    async def set_survey_progress(self, survey_id: str, data: dict) -> bool:
        """Cache survey progress for real-time updates."""
        return await self.set(f"survey:progress:{survey_id}", data, ttl=3600)

    async def get_survey_progress(self, survey_id: str) -> dict | None:
        """Get cached survey progress."""
        return await self.get(f"survey:progress:{survey_id}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
