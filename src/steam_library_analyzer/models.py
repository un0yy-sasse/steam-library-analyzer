from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Game:
    """A single game from a Steam library."""

    appid: int
    name: str
    playtime_minutes: int = 0
    genres: List[str] = field(default_factory=list)

    @property
    def hours(self) -> float:
        return self.playtime_minutes / 60

    @property
    def store_url(self) -> str:
        return f"https://store.steampowered.com/app/{self.appid}"
