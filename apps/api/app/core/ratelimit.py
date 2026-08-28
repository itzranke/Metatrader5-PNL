"""Rate limiter: sliding window.

Production: Redis. Dev/test tanpa Redis: fallback in-memory (per-proses;
catatan: untuk multi-worker production wajib Redis).
"""
import threading
import time
from collections import defaultdict, deque

import redis as redis_lib

from packages.config import get_settings


class RedisBackend:
    def __init__(self, url: str):
        self.client = redis_lib.Redis.from_url(
            url, socket_connect_timeout=1, decode_responses=True
        )

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        pipe = self.client.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zadd(key, {f"{now}:{id(now)}": now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        _, _, count, _ = pipe.execute()
        return count <= limit


class MemoryBackend:
    def __init__(self):
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            dq = self._hits[key]
            while dq and dq[0] < now - window_seconds:
                dq.popleft()
            dq.append(now)
            return len(dq) <= limit

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiter = None


def get_limiter():
    """Singleton — state rate limit harus persisten antar request."""
    global _limiter
    if _limiter is None:
        settings = get_settings()
        _limiter = RedisBackend(settings.redis_url) if settings.redis_url else MemoryBackend()
    return _limiter
