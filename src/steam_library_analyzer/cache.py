"""A tiny JSON file cache for store genre lookups.

The Steam Store API is rate limited (roughly 200 requests per 5 minutes),
so genres are cached on disk and only fetched once per game.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional


def default_cache_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.environ.get("LOCALAPPDATA")
    root = Path(base) if base else Path.home() / ".cache"
    return root / "steam-library-analyzer" / "genres.json"


class GenreCache:
    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else default_cache_path()
        self._data: Dict[str, List[str]] = {}
        self._dirty = False
        self._load()

    def _load(self) -> None:
        try:
            with self.path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self._data = data
        except (FileNotFoundError, json.JSONDecodeError):
            self._data = {}

    def get(self, appid: int) -> Optional[List[str]]:
        return self._data.get(str(appid))

    def set(self, appid: int, genres: List[str]) -> None:
        self._data[str(appid)] = genres
        self._dirty = True

    def __contains__(self, appid: int) -> bool:
        return str(appid) in self._data

    def save(self) -> None:
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(self._data, fh, indent=1, sort_keys=True)
        tmp.replace(self.path)
        self._dirty = False

    def clear(self) -> None:
        self._data = {}
        self._dirty = True
