"""Thin wrappers around the Steam Web API and the Steam Store API."""

from __future__ import annotations

import re
import time
from typing import Callable, Iterable, List, Optional

import requests

from .cache import GenreCache
from .models import Game

WEB_API = "https://api.steampowered.com"
STORE_API = "https://store.steampowered.com/api/appdetails"
UNKNOWN_GENRE = "Unknown"

_STEAMID64 = re.compile(r"^\d{17}$")
_PROFILE_URL = re.compile(r"steamcommunity\.com/(id|profiles)/([^/?#]+)")


class SteamAPIError(RuntimeError):
    pass


class SteamClient:
    def __init__(self, api_key: str, session: Optional[requests.Session] = None,
                 timeout: float = 15.0) -> None:
        if not api_key:
            raise SteamAPIError(
                "No Steam API key. Get one at https://steamcommunity.com/dev/apikey "
                "and pass --api-key or set STEAM_API_KEY."
            )
        self.api_key = api_key
        self.session = session or requests.Session()
        self.session.headers.setdefault("User-Agent", "steam-library-analyzer")
        self.timeout = timeout

    # ------------------------------------------------------------------ users
    def resolve_steam_id(self, user: str) -> str:
        """Accept a SteamID64, a vanity name or a full profile URL."""
        user = user.strip()
        match = _PROFILE_URL.search(user)
        if match:
            kind, value = match.groups()
            if kind == "profiles":
                return value
            user = value
        if _STEAMID64.match(user):
            return user

        data = self._get(
            f"{WEB_API}/ISteamUser/ResolveVanityURL/v1/",
            {"key": self.api_key, "vanityurl": user},
        )
        resp = data.get("response", {})
        if resp.get("success") != 1:
            raise SteamAPIError(f"Could not resolve Steam user '{user}'.")
        return resp["steamid"]

    # ------------------------------------------------------------------ games
    def owned_games(self, steam_id: str) -> List[Game]:
        data = self._get(
            f"{WEB_API}/IPlayerService/GetOwnedGames/v1/",
            {
                "key": self.api_key,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1,
            },
        )
        resp = data.get("response", {})
        if "games" not in resp:
            raise SteamAPIError(
                "No games returned. Is the profile's 'Game details' privacy "
                "setting set to Public?"
            )
        return [
            Game(
                appid=int(g["appid"]),
                name=g.get("name") or f"App {g['appid']}",
                playtime_minutes=int(g.get("playtime_forever", 0)),
            )
            for g in resp["games"]
        ]

    # ----------------------------------------------------------------- genres
    def fetch_genres(self, appid: int) -> List[str]:
        """Look up a game's genres on the Steam Store. Returns [] if unknown."""
        for attempt in range(4):
            r = self.session.get(
                STORE_API,
                params={"appids": appid, "filters": "genres", "l": "english"},
                timeout=self.timeout,
            )
            if r.status_code == 429:  # rate limited: back off and retry
                time.sleep(10 * (attempt + 1))
                continue
            r.raise_for_status()
            entry = (r.json() or {}).get(str(appid)) or {}
            if not entry.get("success"):
                return []
            data = entry.get("data") or {}
            if not isinstance(data, dict):
                return []
            return [g["description"] for g in data.get("genres", []) if "description" in g]
        raise SteamAPIError("Steam Store rate limit hit repeatedly; try again later.")

    def attach_genres(
        self,
        games: Iterable[Game],
        cache: GenreCache,
        delay: float = 1.5,
        progress: Optional[Callable[[Game], None]] = None,
    ) -> None:
        """Fill in ``game.genres`` from the cache, fetching missing ones."""
        try:
            for game in games:
                cached = cache.get(game.appid)
                if cached is None:
                    cached = self.fetch_genres(game.appid)
                    cache.set(game.appid, cached)
                    if delay:
                        time.sleep(delay)
                game.genres = cached or [UNKNOWN_GENRE]
                if progress:
                    progress(game)
        finally:
            cache.save()  # keep progress even if interrupted

    # --------------------------------------------------------------- helpers
    def _get(self, url: str, params: dict) -> dict:
        try:
            r = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise SteamAPIError(f"Network error: {exc}") from exc
        if r.status_code in (401, 403):
            raise SteamAPIError("Steam rejected the request. Check your API key.")
        if not r.ok:
            raise SteamAPIError(f"Steam API returned HTTP {r.status_code}.")
        return r.json()
