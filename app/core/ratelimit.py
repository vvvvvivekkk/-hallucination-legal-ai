from __future__ import annotations

import threading
import time
from typing import Any

from ..core.exceptions import RateLimitExceededError
from ..core.logger import get_logger

logger = get_logger(__name__)


class RedisRateLimiter:
    """Sliding-window rate limiter backed by Redis."""

    def __init__(self, redis_client: Any, prefix: str = "legal-ai:rl:") -> None:
        self._redis = redis_client
        self._prefix = prefix

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        full_key = f"{self._prefix}{key}"
        now_ms = int(time.time() * 1000)
        window_start = now_ms - window_seconds * 1000
        pipeline = self._redis.pipeline()
        pipeline.zremrangebyscore(full_key, 0, window_start)
        pipeline.zadd(full_key, {str(now_ms): now_ms})
        pipeline.zcard(full_key)
        pipeline.expire(full_key, window_seconds)
        _, _, count, _ = pipeline.execute()
        return int(count) <= limit


class InMemoryRateLimiter:
    """Thread-safe sliding-window limiter used when Redis is unavailable."""

    def __init__(self) -> None:
        self._buckets: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            stamps = [
                stamp
                for stamp in self._buckets.get(key, [])
                if stamp > now - window_seconds
            ]
            if len(stamps) >= limit:
                self._buckets[key] = stamps
                return False
            stamps.append(now)
            self._buckets[key] = stamps
            return True


class RateLimiter:
    """Composite limiter; prefers Redis, degrades to in-memory."""

    def __init__(
        self,
        redis_client: Any | None = None,
        prefix: str = "legal-ai:rl:",
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled
        if redis_client is not None:
            self._backend = RedisRateLimiter(redis_client, prefix)
        else:
            self._backend = InMemoryRateLimiter()

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        if not self._enabled:
            return True
        return self._backend.hit(key, limit, window_seconds)

    def check(self, key: str, limit: int, window_seconds: int) -> None:
        if not self.hit(key, limit, window_seconds):
            raise RateLimitExceededError(
                f"rate limit exceeded: {limit} requests per {window_seconds}s"
            )
