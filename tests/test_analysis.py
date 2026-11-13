from steam_library_analyzer import analysis
from steam_library_analyzer.models import Game

GAMES = [
    Game(1, "Portal 2", 600, ["Action", "Adventure"]),
    Game(2, "Stardew Valley", 3000, ["Indie", "RPG", "Simulation"]),
    Game(3, "Backlog Game", 0, ["RPG"]),
    Game(4, "Tried Once", 30, ["Action"]),
    Game(5, "No Genre", 0, []),
]


def test_summary():
    s = analysis.summarize(GAMES, barely_played_minutes=120)
    assert s.total_games == 5
    assert s.played_games == 3
    assert s.unplayed_games == 2
    assert s.total_minutes == 3630
    assert s.barely_played_games == 1
    assert s.unplayed_percent == 40.0


def test_summary_empty_library():
    s = analysis.summarize([])
    assert s.total_games == 0
    assert s.unplayed_percent == 0.0


def test_hours_by_genre_full_counting():
    stats = {s.genre: s for s in analysis.hours_by_genre(GAMES)}
    assert stats["Action"].minutes == 630
    assert stats["RPG"].minutes == 3000
    assert stats["RPG"].games == 2
    assert stats["RPG"].unplayed == 1
    assert stats["Unknown"].games == 1
    # sorted by playtime, descending
    ordered = [s.genre for s in analysis.hours_by_genre(GAMES)]
    assert ordered[0] in {"Indie", "RPG", "Simulation"}


def test_hours_by_genre_split_adds_up():
    stats = analysis.hours_by_genre(GAMES, split=True)
    assert sum(s.minutes for s in stats) == 3630
    by = {s.genre: s for s in stats}
    assert by["Action"].minutes == 300 + 30


def test_top_unplayed_barely():
    assert [g.name for g in analysis.top_games(GAMES, 2)] == ["Stardew Valley", "Portal 2"]
    assert [g.name for g in analysis.unplayed_games(GAMES)] == ["Backlog Game", "No Genre"]
    assert [g.name for g in analysis.barely_played_games(GAMES, 120)] == ["Tried Once"]
