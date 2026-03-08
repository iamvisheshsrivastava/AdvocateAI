import json
import os
import time
from hashlib import sha256
from threading import Lock
from typing import Any

try:
    import redis
except Exception:
    redis = None


class CacheService:
    def __init__(self):
        self._lock = Lock()
        self._memory_cache: dict[str, tuple[float, str]] = {}
        self._memory_counters: dict[str, tuple[float, int]] = {}
        self._redis = self._build_redis_client()

    def _build_redis_client(self):
        if redis is None:
            return None

        host = os.getenv("REDIS_HOST", "localhost").strip()
        port = int(os.getenv("REDIS_PORT", "6379"))

        try:
            client = redis.Redis(host=host, port=port, db=0, decode_responses=True)
            client.ping()
            return client
        except Exception:
            return None

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    def make_hash(self, value: str) -> str:
        return sha256((value or "").encode("utf-8")).hexdigest()

    def get(self, key: str) -> Any:
        if self._redis is not None:
            try:
                value = self._redis.get(key)
                if value is not None:
                    return json.loads(value)
            except Exception:
                pass

        with self._lock:
            entry = self._memory_cache.get(key)
            if not entry:
                return None

            expires_at, raw_value = entry
            if expires_at < time.time():
                self._memory_cache.pop(key, None)
                return None

            try:
                return json.loads(raw_value)
            except Exception:
                return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        serialized = json.dumps(value)

        if self._redis is not None:
            try:
                self._redis.setex(key, ttl_seconds, serialized)
                return
            except Exception:
                pass

        with self._lock:
            self._memory_cache[key] = (time.time() + ttl_seconds, serialized)

    def allow_request(self, bucket: str, identifier: str, limit: int, window_seconds: int) -> bool:
        key = f"rate_limit:{bucket}:{identifier}"

        if self._redis is not None:
            try:
                current = self._redis.incr(key)
                if current == 1:
                    self._redis.expire(key, window_seconds)
                return int(current) <= limit
            except Exception:
                pass

        with self._lock:
            now = time.time()
            expires_at, count = self._memory_counters.get(key, (now + window_seconds, 0))
            if expires_at < now:
                expires_at = now + window_seconds
                count = 0

            count += 1
            self._memory_counters[key] = (expires_at, count)
            return count <= limit


cache_service = CacheService()
