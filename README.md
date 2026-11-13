# Steam Library Analyzer

See where your gaming hours really go. Steam Library Analyzer pulls your Steam library and tells you:

- **How many hours you've spent per genre**, with a bar chart in the terminal
- **Your most played games**
- **Your backlog**: games you own but have never launched, plus the ones you barely touched
- An optional **JSON / CSV export** of everything for spreadsheets or your own charts

```
╭──────────────────────────── Steam Library ─────────────────────────────╮
│ 312 games  ·  2,481 hours played                                       │
│ 187 played  ·  125 never launched (40% of your library)  ·  41 played < 2h │
╰────────────────────────────────────────────────────────────────────────╯
Hours by genre
┏━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓
┃ Genre        ┃  Hours ┃                          ┃ Games ┃ Unplayed ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩
│ Action       │ 1,204.5│ ████████████████████████ │   143 │       52 │
│ Indie        │   812.0│ ████████████████░░░░░░░░ │   121 │       49 │
│ RPG          │   640.3│ █████████████░░░░░░░░░░░ │    48 │       17 │
│ Strategy     │   210.8│ ████░░░░░░░░░░░░░░░░░░░░ │    31 │       14 │
└──────────────┴────────┴──────────────────────────┴───────┴──────────┘
```

*(example output)*

## Requirements

- Python 3.9+
- A free **Steam Web API key**: <https://steamcommunity.com/dev/apikey>
- Your Steam profile's **Game details** set to **Public**
  (Steam → Profile → Edit Profile → Privacy Settings)

## Installation

```bash
git clone https://github.com/<your-username>/steam-library-analyzer.git
cd steam-library-analyzer
pip install .
```

## Usage

```bash
# Set your key once (or pass --api-key every time)
export STEAM_API_KEY=your_key_here          # macOS / Linux
$env:STEAM_API_KEY = "your_key_here"        # Windows PowerShell

# Analyze by vanity name, SteamID64 or profile URL
steam-analyzer gabelogannewell
steam-analyzer 76561197960287930
steam-analyzer https://steamcommunity.com/id/gabelogannewell
```

The first run looks up each game's genres on the Steam Store. The store is rate limited, so this takes about 1.5 s per game. A large library can take a few minutes. Results are cached, so later runs are instant. If you interrupt the run, everything fetched so far is kept.

### Options

| Option | Description |
| --- | --- |
| `--no-genres` | Skip genre lookups (instant, no store requests) |
| `--split-genres` | Divide a game's hours between its genres instead of counting them in full for each genre |
| `--top N` | Number of most played games to show (default 10) |
| `--barely-played HOURS` | Threshold for "barely played" (default 2) |
| `--unplayed-limit N` | How many unplayed games to list, `0` to hide (default 25) |
| `--json FILE` | Export summary, genres and games as JSON |
| `--csv FILE` | Export every game (hours, genres, store link) as CSV |
| `--cache FILE` | Custom location for the genre cache |
| `--refresh-cache` | Re-fetch all genres |
| `--delay SECONDS` | Pause between store requests (default 1.5) |

### How genre hours are counted

Most games have several genres. By default, a game's full playtime counts toward **each** of its genres. That shows "how much time did I spend in games that are RPGs", but the genre totals add up to more than your total playtime. Use `--split-genres` to split the hours evenly so the totals add up exactly.

## Development

```bash
pip install -e ".[dev]"
pytest
```

The tests don't touch the network. The analysis logic (`analysis.py`) contains only pure functions, and the API client is tested with a fake HTTP session.

```
src/steam_library_analyzer/
├── cli.py         # argument parsing and the main flow
├── steam_api.py   # Steam Web API + Store API client
├── cache.py       # on-disk genre cache
├── analysis.py    # summary, hours per genre, top/unplayed games
├── report.py      # terminal tables, JSON and CSV export
└── models.py      # Game dataclass
```

## Ideas / Roadmap

- [ ] HTML report with charts
- [ ] Compare two libraries (you vs. a friend)
- [ ] "What should I play next?" picks from the backlog
- [ ] Playtime in the last two weeks
- [ ] Price data: how much did your unplayed games cost?

## License

MIT. Not affiliated with Valve or Steam.
