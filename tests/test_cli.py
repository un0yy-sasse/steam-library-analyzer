import csv
import json

from steam_library_analyzer import cli
from steam_library_analyzer.models import Game


class StubClient:
    def __init__(self, api_key):
        self.api_key = api_key

    def resolve_steam_id(self, user):
        return "76561197960287930"

    def owned_games(self, steam_id):
        return [
            Game(620, "Portal 2", 600),
            Game(413150, "Stardew Valley", 3000),
            Game(1, "Backlog Game", 0),
        ]

    def attach_genres(self, games, cache, delay=0, progress=None):
        for g in games:
            g.genres = ["Indie"] if g.appid == 413150 else ["Action"]
            if progress:
                progress(g)


def test_cli_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "SteamClient", StubClient)
    out_json = tmp_path / "report.json"
    out_csv = tmp_path / "games.csv"

    code = cli.main(["someone", "--api-key", "KEY", "--cache", str(tmp_path / "c.json"),
                     "--json", str(out_json), "--csv", str(out_csv)])

    assert code == 0
    printed = capsys.readouterr().out
    assert "Stardew Valley" in printed
    assert "Backlog Game" in printed

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["summary"]["unplayed_games"] == 1
    assert data["genres"][0]["genre"] == "Indie"

    rows = list(csv.DictReader(out_csv.open(encoding="utf-8")))
    assert rows[0]["name"] == "Stardew Valley"
    assert len(rows) == 3


def test_cli_missing_key(monkeypatch, capsys):
    monkeypatch.delenv("STEAM_API_KEY", raising=False)
    assert cli.main(["someone", "--api-key", ""]) == 1
    assert "API key" in capsys.readouterr().out
