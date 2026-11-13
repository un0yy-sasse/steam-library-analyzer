import json

import pytest

from steam_library_analyzer.cache import GenreCache
from steam_library_analyzer.steam_api import SteamAPIError, SteamClient


class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    @property
    def ok(self):
        return self.status_code < 400

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(self.status_code)


class FakeSession:
    """Routes requests by URL substring to canned payloads."""

    def __init__(self, routes):
        self.routes = routes
        self.headers = {}
        self.calls = []

    def get(self, url, params=None, timeout=None):
        self.calls.append((url, params))
        for key, handler in self.routes.items():
            if key in url:
                return handler(params) if callable(handler) else FakeResponse(handler)
        raise AssertionError(f"unexpected URL {url}")


def make_client(routes):
    return SteamClient("KEY", session=FakeSession(routes))


def test_missing_key():
    with pytest.raises(SteamAPIError):
        SteamClient("")


@pytest.mark.parametrize("user,expected", [
    ("76561197960287930", "76561197960287930"),
    ("https://steamcommunity.com/profiles/76561197960287930/", "76561197960287930"),
])
def test_resolve_without_network(user, expected):
    client = make_client({})
    assert client.resolve_steam_id(user) == expected


def test_resolve_vanity_and_url():
    client = make_client({"ResolveVanityURL": {"response": {"success": 1, "steamid": "123"}}})
    assert client.resolve_steam_id("gaben") == "123"
    assert client.resolve_steam_id("https://steamcommunity.com/id/gaben") == "123"
    assert client.session.calls[-1][1]["vanityurl"] == "gaben"


def test_resolve_failure():
    client = make_client({"ResolveVanityURL": {"response": {"success": 42}}})
    with pytest.raises(SteamAPIError):
        client.resolve_steam_id("nobody")


def test_owned_games():
    client = make_client({"GetOwnedGames": {"response": {"game_count": 2, "games": [
        {"appid": 620, "name": "Portal 2", "playtime_forever": 125},
        {"appid": 999, "playtime_forever": 0},
    ]}}})
    games = client.owned_games("1")
    assert [(g.appid, g.name, g.playtime_minutes) for g in games] == [
        (620, "Portal 2", 125), (999, "App 999", 0)]


def test_owned_games_private_profile():
    client = make_client({"GetOwnedGames": {"response": {}}})
    with pytest.raises(SteamAPIError, match="Public"):
        client.owned_games("1")


def test_attach_genres_uses_cache(tmp_path):
    store = {
        "620": {"success": True, "data": {"genres": [{"id": "1", "description": "Action"}]}},
        "999": {"success": False},
    }
    client = make_client({"appdetails": lambda p: FakeResponse({str(p["appids"]): store[str(p["appids"])]})})
    cache_file = tmp_path / "genres.json"
    cache = GenreCache(cache_file)
    games = make_client({"GetOwnedGames": {"response": {"games": [
        {"appid": 620, "name": "Portal 2"}, {"appid": 999, "name": "Delisted"}]}}}).owned_games("1")

    client.attach_genres(games, cache, delay=0)
    assert games[0].genres == ["Action"]
    assert games[1].genres == ["Unknown"]
    assert json.loads(cache_file.read_text()) == {"620": ["Action"], "999": []}

    # second run: everything comes from the cache, no store requests
    calls_before = len(client.session.calls)
    client.attach_genres(games, GenreCache(cache_file), delay=0)
    assert len(client.session.calls) == calls_before
