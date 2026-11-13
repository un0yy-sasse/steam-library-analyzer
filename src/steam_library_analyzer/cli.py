from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

from . import __version__
from .cache import GenreCache
from .report import export_csv, export_json, print_report
from .steam_api import SteamAPIError, SteamClient


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="steam-analyzer",
        description="Analyze a Steam library: hours per genre, top games and the backlog "
                    "of games you've never played.",
    )
    p.add_argument("user", help="SteamID64, vanity name or profile URL "
                                "(e.g. https://steamcommunity.com/id/gabelogannewell)")
    p.add_argument("--api-key", default=os.environ.get("STEAM_API_KEY"),
                   help="Steam Web API key (default: $STEAM_API_KEY)")
    p.add_argument("--no-genres", action="store_true",
                   help="skip genre lookups (fast, no store requests)")
    p.add_argument("--split-genres", action="store_true",
                   help="divide a game's hours between its genres instead of "
                        "counting them fully for each")
    p.add_argument("--top", type=int, default=10, help="number of top games to show (default 10)")
    p.add_argument("--barely-played", type=float, default=2, metavar="HOURS",
                   help="threshold for 'barely played' games in hours (default 2)")
    p.add_argument("--unplayed-limit", type=int, default=25, metavar="N",
                   help="max unplayed games to list, 0 to hide (default 25)")
    p.add_argument("--json", type=Path, metavar="FILE", help="export results as JSON")
    p.add_argument("--csv", type=Path, metavar="FILE", help="export all games as CSV")
    p.add_argument("--cache", type=Path, metavar="FILE", help="genre cache file location")
    p.add_argument("--refresh-cache", action="store_true", help="re-fetch all genres")
    p.add_argument("--delay", type=float, default=1.5,
                   help="seconds between store requests (default 1.5, avoids rate limits)")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    console = Console()

    try:
        client = SteamClient(args.api_key)
        steam_id = client.resolve_steam_id(args.user)
        with console.status("Fetching owned games…"):
            games = client.owned_games(steam_id)

        if not args.no_genres:
            cache = GenreCache(args.cache)
            if args.refresh_cache:
                cache.clear()
            missing = sum(1 for g in games if g.appid not in cache)
            if missing:
                eta = missing * (args.delay + 0.3)
                console.print(f"[dim]Looking up genres for {missing} games "
                              f"(~{eta / 60:.0f} min the first time, cached afterwards)…[/]")
            with Progress(TextColumn("[progress.description]{task.description}"),
                          BarColumn(), MofNCompleteColumn(), console=console,
                          transient=True) as progress:
                task = progress.add_task("Genres", total=len(games))
                client.attach_genres(games, cache, delay=args.delay,
                                     progress=lambda _g: progress.advance(task))
    except SteamAPIError as exc:
        console.print(f"[red]Error:[/] {exc}")
        return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted. Genres fetched so far are cached.[/]")
        return 130

    print_report(
        console, games,
        with_genres=not args.no_genres,
        split_genres=args.split_genres,
        top=args.top,
        barely_minutes=int(args.barely_played * 60),
        show_unplayed=args.unplayed_limit,
    )

    if args.json:
        export_json(args.json, games, split_genres=args.split_genres)
        console.print(f"[green]Saved JSON →[/] {args.json}")
    if args.csv:
        export_csv(args.csv, games)
        console.print(f"[green]Saved CSV →[/] {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
