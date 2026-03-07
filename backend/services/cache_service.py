from typing import Any


class CacheService:
    def get(self, key: str) -> Any:
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        return


cache_service = CacheService()
