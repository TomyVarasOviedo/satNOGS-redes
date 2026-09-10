import json
import os
import time
from pathlib import Path
from typing import Any, Optional
from utils.config import RESILIENCE_CONFIG


class CacheManager:
    def __init__(self, cache_dir: Optional[str] = None):
        self.cache_dir = Path(cache_dir or RESILIENCE_CONFIG["CACHE_DIR"])
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _key_for(self, endpoint: str, params: dict) -> str:
        param_str = "_".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{endpoint}_{param_str}.json" if param_str else f"{endpoint}.json"

    def _cache_path(self, key: str) -> Path:
        return self.cache_dir / key

    def get(self, endpoint: str, params: dict, ttl: int) -> tuple[Optional[Any], Optional[str], Optional[int]]:
        key = self._key_for(endpoint, params)
        path = self._cache_path(key)

        if not path.exists():
            return None, None, None

        try:
            with open(path, "r") as f:
                data = json.load(f)

            cached_at = data.get("_cached_at", 0)
            age = int(time.time() - cached_at)

            if age > ttl:
                return data.get("data"), "stale", age

            return data.get("data"), "cache", age

        except (json.JSONDecodeError, OSError):
            return None, None, None

    def set(self, endpoint: str, params: dict, data: Any) -> None:
        key = self._key_for(endpoint, params)
        path = self._cache_path(key)

        payload = {
            "data": data,
            "_cached_at": time.time(),
        }

        temp_path = path.with_suffix(".tmp")
        try:
            with open(temp_path, "w") as f:
                json.dump(payload, f)
            temp_path.replace(path)
        except OSError:
            if temp_path.exists():
                temp_path.unlink()

    def delete(self, endpoint: str, params: dict) -> None:
        key = self._key_for(endpoint, params)
        path = self._cache_path(key)
        if path.exists():
            path.unlink()

    def clear(self) -> None:
        for file in self.cache_dir.glob("*.json"):
            file.unlink()


cache_manager = CacheManager()