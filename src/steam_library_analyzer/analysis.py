"""Pure analysis functions - no network, easy to test."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Sequence

from .models import Game


@dataclass
class GenreStats:
    genre: str
    games: int
    played: int
    minutes: int

    @property
    def hours(self) -> float:
        return self.minutes / 60

    @property
    def unplayed(self) -> int:
        return self.games - self.played


@dataclass
class LibrarySummary:
    total_games: int
    played_games: int
    unplayed_games: int
    total_minutes: int
    barely_played_games: int

    @property
    def total_hours(self) -> float:
        return self.total_minutes / 60

    @property
    def unplayed_percent(self) -> float:
        return 100 * self.unplayed_games / self.total_games if self.total_games else 0.0


def summarize(games: Sequence[Game], barely_played_minutes: int = 120) -> LibrarySummary:
    played = [g for g in games if g.playtime_minutes > 0]
    barely = [g for g in played if g.playtime_minutes < barely_played_minutes]
    return LibrarySummary(
        total_games=len(games),
        played_games=len(played),
        unplayed_games=len(games) - len(played),
        total_minutes=sum(g.playtime_minutes for g in games),
        barely_played_games=len(barely),
    )


def hours_by_genre(games: Sequence[Game], split: bool = False) -> List[GenreStats]:
    """Aggregate playtime per genre, sorted by playtime (desc).

    A game usually has several genres. By default its full playtime counts
    toward *each* of them (so genre totals add up to more than your total
    playtime). With ``split=True`` the playtime is divided evenly between
    the game's genres, so the totals add up exactly.
    """
    minutes: Dict[str, float] = defaultdict(float)
    count: Dict[str, int] = defaultdict(int)
    played: Dict[str, int] = defaultdict(int)

    for game in games:
        genres = game.genres or ["Unknown"]
        share = game.playtime_minutes / len(genres) if split else game.playtime_minutes
        for genre in genres:
            minutes[genre] += share
            count[genre] += 1
            if game.playtime_minutes > 0:
                played[genre] += 1

    stats = [
        GenreStats(genre=g, games=count[g], played=played[g], minutes=round(minutes[g]))
        for g in count
    ]
    stats.sort(key=lambda s: (-s.minutes, -s.games, s.genre))
    return stats


def top_games(games: Sequence[Game], limit: int = 10) -> List[Game]:
    ranked = sorted(
        (g for g in games if g.playtime_minutes > 0),
        key=lambda g: (-g.playtime_minutes, g.name.lower()),
    )
    return ranked[:limit]


def unplayed_games(games: Sequence[Game]) -> List[Game]:
    return sorted((g for g in games if g.playtime_minutes == 0), key=lambda g: g.name.lower())


def barely_played_games(games: Sequence[Game], max_minutes: int = 120) -> List[Game]:
    return sorted(
        (g for g in games if 0 < g.playtime_minutes < max_minutes),
        key=lambda g: (g.playtime_minutes, g.name.lower()),
    )
