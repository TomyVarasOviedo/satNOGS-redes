from __future__ import annotations

import json
import os
import time
from pathlib import Path


class State:
    """Datos pequeños de deduplicación, guardados en JSON con escritura atómica."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._data: dict[str, float] = self._load()

    def _load(self) -> dict[str, float]:
        try:
            with open(self.path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            str(key): float(value)
            for key, value in payload.items()
            if isinstance(value, (int, float))
        }

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            with open(temp, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, indent=2)
            os.replace(temp, self.path)
        except OSError:
            temp.unlink(missing_ok=True)

    def contains(self, key: str) -> bool:
        return key in self._data

    def mark(self, key: str, timestamp: float | None = None) -> None:
        self._data[key] = time.time() if timestamp is None else timestamp
        self._save()

    def prune(self, max_age_days: float = 3) -> None:
        cutoff = time.time() - max_age_days * 86400
        old = [key for key, timestamp in self._data.items() if timestamp < cutoff]
        if not old:
            return
        for key in old:
            self._data.pop(key, None)
        self._save()
