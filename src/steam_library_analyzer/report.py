"""Rendering: rich terminal output plus JSON / CSV export."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Sequence

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import analysis
from .models import Game


def _bar(value: float, maximum: float, width: int = 24) -> str:
    if maximum <= 0:
        return ""
    filled = round(width * value / maximum)
    return "█" * filled + "░" * (width - filled)


def print_report(
    console: Console,
    games: Sequence[Game],
    *,
    with_genres: bool,
    split_genres: bool = False,
    top: int = 10,
    barely_minutes: int = 120,
    show_unplayed: int = 25,
) -> None:
    s = analysis.summarize(games, barely_minutes)

    console.print(Panel.fit(
        f"[bold]{s.total_games}[/] games  ·  [bold]{s.total_hours:,.0f}[/] hours played\n"
        f"[green]{s.played_games}[/] played  ·  [red]{s.unplayed_games}[/] never launched "
        f"([red]{s.unplayed_percent:.0f}%[/] of your library)  ·  "
        f"[yellow]{s.barely_played_games}[/] played < {barely_minutes // 60 or 1}h",
        title="Steam Library",
        border_style="cyan",
    ))

    if with_genres:
        stats = analysis.hours_by_genre(games, split=split_genres)
        t = Table(title="Hours by genre" + (" (split)" if split_genres else ""),
                  title_justify="left")
        t.add_column("Genre")
        t.add_column("Hours", justify="right")
        t.add_column("", no_wrap=True)
        t.add_column("Games", justify="right")
        t.add_column("Unplayed", justify="right")
        top_minutes = stats[0].minutes if stats else 0
        for st in stats:
            t.add_row(st.genre, f"{st.hours:,.1f}", f"[cyan]{_bar(st.minutes, top_minutes)}[/]",
                      str(st.games), str(st.unplayed))
        console.print(t)
        if not split_genres:
            console.print("[dim]A game's hours count toward every genre it has. "
                          "Use --split-genres to divide them instead.[/]\n")

    t = Table(title=f"Top {top} most played", title_justify="left")
    t.add_column("#", justify="right")
    t.add_column("Game")
    t.add_column("Hours", justify="right")
    if with_genres:
        t.add_column("Genres", style="dim")
    for i, g in enumerate(analysis.top_games(games, top), 1):
        row = [str(i), g.name, f"{g.hours:,.1f}"]
        if with_genres:
            row.append(", ".join(g.genres))
        t.add_row(*row)
    console.print(t)

    unplayed = analysis.unplayed_games(games)
    if unplayed and show_unplayed:
        t = Table(title=f"Never played ({len(unplayed)})", title_justify="left")
        t.add_column("Game")
        if with_genres:
            t.add_column("Genres", style="dim")
        for g in unplayed[:show_unplayed]:
            if with_genres:
                t.add_row(g.name, ", ".join(g.genres))
            else:
                t.add_row(g.name)
        console.print(t)
        if len(unplayed) > show_unplayed:
            console.print(f"[dim]…and {len(unplayed) - show_unplayed} more "
                          "(use --unplayed-limit 0 to hide, or --csv to export all).[/]")


def export_json(path: Path, games: Sequence[Game], split_genres: bool = False) -> None:
    s = analysis.summarize(games)
    payload = {
        "summary": {
            "total_games": s.total_games,
            "played_games": s.played_games,
            "unplayed_games": s.unplayed_games,
            "total_hours": round(s.total_hours, 1),
        },
        "genres": [
            {"genre": st.genre, "hours": round(st.hours, 1), "games": st.games,
             "unplayed": st.unplayed}
            for st in analysis.hours_by_genre(games, split=split_genres)
        ],
        "games": [
            {"appid": g.appid, "name": g.name, "hours": round(g.hours, 1), "genres": g.genres}
            for g in sorted(games, key=lambda g: -g.playtime_minutes)
        ],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def export_csv(path: Path, games: Sequence[Game]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["appid", "name", "hours", "played", "genres", "store_url"])
        for g in sorted(games, key=lambda g: -g.playtime_minutes):
            w.writerow([g.appid, g.name, f"{g.hours:.1f}", g.playtime_minutes > 0,
                        "; ".join(g.genres), g.store_url])
