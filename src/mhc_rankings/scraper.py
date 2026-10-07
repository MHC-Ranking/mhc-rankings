"""Convert GameSheet results into the TSV read by `mhc_rankings.io`.

Given a games-page URL, results are read from the site's own paged JSON
endpoint, which returns every game (the page itself embeds only the first 25).
Given a saved HTML file, only the games embedded in that page are returned.
The site may serve a bot challenge, in which case a saved page from a browser
is needed.
"""

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from .teams import Roster, UnknownTeamError, load_roster

TSV_HEADER = ["Date", "Away Team", "Score", "Home Team", "Location", "Game ID", "Overtime", "Game URL"]
DATE_FORMAT = "%b %d, %Y"
GAME_URL = "https://gamesheetstats.com/seasons/{season_id}/games/{game_id}"
API_URL = "https://gamesheetstats.com/api/unified-games/{season_id}"
API_PAGE_SIZE = 100
USER_AGENT = {"User-Agent": "mhc-rankings/0.1"}
_SEASON_RE = re.compile(r"/seasons/(\d+)/")
_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')
_GAMES_RE = re.compile(r'"games":\[')
_REGULATION_PERIODS = {"1", "2", "3", "final"}
_BLOCK_MARKERS = ("Just a moment...", "_cf_chl_opt")
_BLOCKED_MESSAGE = "Site returned a bot challenge; save the page from a browser and pass the file."


class ScrapeBlockedError(RuntimeError):
    """Raised when the site returns a bot-challenge page instead of results."""


@dataclass(frozen=True)
class Game:
    """One completed game as listed on the results page."""

    date: str
    away: str
    away_score: int
    home_score: int
    home: str
    location: str
    game_id: str
    overtime: str
    game_url: str = ""

    def as_row(self) -> list[str]:
        """Return the game as a TSV row matching `TSV_HEADER`."""
        score = f"{self.away_score}-{self.home_score}"
        return [self.date, self.away, score, self.home, self.location, self.game_id, self.overtime, self.game_url]


def _embedded_text(html: str) -> str:
    """Join the Next.js flight-data string chunks embedded in the page."""
    return "".join(json.loads(f'"{chunk}"') for chunk in _PUSH_RE.findall(html))


def _game_dicts(text: str) -> list[dict[str, Any]]:
    """Return the game objects from every `"games":[...]` array in the payload."""
    decoder = json.JSONDecoder()
    games: list[dict[str, Any]] = []
    for match in _GAMES_RE.finditer(text):
        array, _ = decoder.raw_decode(text, match.end() - 1)
        games.extend(array)
    return games


def _overtime_marker(team: dict[str, Any]) -> str:
    """Return 'OT' when the team's per-period goals include extra periods."""
    return "OT" if any(p not in _REGULATION_PERIODS for p in team.get("goalsByPeriod", {})) else ""


def _tie_marker(game: dict[str, Any]) -> str:
    """Return 'OT' when the final scores are equal, since a tied game went to overtime."""
    return "OT" if game["visitor"]["goals"] == game["home"]["goals"] else ""


def season_id_from_url(source: str) -> str:
    """Return the GameSheet season id in a `/seasons/<id>/` URL, or "" if there is none."""
    match = _SEASON_RE.search(source)
    return match.group(1) if match else ""


def games_from_dicts(raw: list[dict[str, Any]], season_id: str = "") -> list[Game]:
    """Return the final games in `raw`, de-duplicated and oldest first.

    Each game gets a GameSheet page link when `season_id` is given, otherwise a blank one.
    """
    final = {g["gameId"]: g for g in raw if g.get("status") == "final"}
    games = [
        Game(
            date=g["date"],
            away=g["visitor"]["title"],
            away_score=g["visitor"]["goals"],
            home_score=g["home"]["goals"],
            home=g["home"]["title"],
            location=g["location"],
            game_id=g["number"],
            overtime=_overtime_marker(g["visitor"]) or _overtime_marker(g["home"]) or _tie_marker(g),
            game_url=GAME_URL.format(season_id=season_id, game_id=g["gameId"]) if season_id else "",
        )
        for g in final.values()
    ]
    return sorted(games, key=lambda g: datetime.strptime(g.date, DATE_FORMAT))


def parse_games(html: str, season_id: str = "") -> list[Game]:
    """Extract final games embedded in page HTML, de-duplicated and oldest first.

    Raises:
        ScrapeBlockedError: If the HTML is a bot-challenge page.
        ValueError: If the page contains no embedded game data.
    """
    if any(marker in html for marker in _BLOCK_MARKERS):
        raise ScrapeBlockedError(_BLOCKED_MESSAGE)

    raw = _game_dicts(_embedded_text(html))
    if not raw:
        raise ValueError("No embedded game data found in the page.")
    return games_from_dicts(raw, season_id)


def _get_json(url: str) -> dict[str, Any]:
    """Return the JSON object at `url`.

    Raises:
        ScrapeBlockedError: If the site refuses the request or answers with a non-JSON challenge page.
    """
    request = urllib.request.Request(url, headers=USER_AGENT)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        if exc.code in (403, 429, 503):
            raise ScrapeBlockedError(_BLOCKED_MESSAGE) from exc
        raise
    except json.JSONDecodeError as exc:
        raise ScrapeBlockedError(_BLOCKED_MESSAGE) from exc


def fetch_game_dicts(source: str) -> list[dict[str, Any]]:
    """Return every game matching the division and type filters of a GameSheet games-page URL.

    The page shows only its first 25 games, so this reads the site's own paged JSON endpoint instead.
    """
    filters = urllib.parse.parse_qs(urllib.parse.urlsplit(source).query)
    params = {"order": "asc", "limit": str(API_PAGE_SIZE)}
    if "filter[division]" in filters:
        params["division"] = filters["filter[division]"][0]
    if "filter[type]" in filters:
        params["gameType"] = filters["filter[type]"][0]
    url = API_URL.format(season_id=season_id_from_url(source))

    games: list[dict[str, Any]] = []
    while True:
        page = _get_json(f"{url}?{urllib.parse.urlencode({**params, 'offset': len(games)})}")
        games.extend(page["data"])
        if not page["data"] or len(games) >= page["meta"]["filtered"]:
            return games


def load_games(source: str, season_id: str = "") -> list[Game]:
    """Return the final games from a GameSheet URL (all pages) or a saved HTML file (embedded games only).

    Raises:
        ScrapeBlockedError: If the site serves a bot challenge.
        ValueError: If there are no games.
    """
    if not source.startswith(("http://", "https://")):
        return parse_games(Path(source).read_text(encoding="utf-8"), season_id)
    games = games_from_dicts(fetch_game_dicts(source), season_id)
    if not games:
        raise ValueError("No completed games found.")
    return games


def canonicalize(games: list[Game], roster: Roster) -> list[Game]:
    """Return `games` with team names replaced by the roster's canonical names.

    Raises:
        UnknownTeamError: If a game names a team that is not in the roster.
    """
    return [replace(g, away=roster.resolve(g.away).name, home=roster.resolve(g.home).name) for g in games]


def write_tsv(games: list[Game], output: Path) -> None:
    """Write games to `output` in the ratings-software TSV format."""
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(TSV_HEADER)
        writer.writerows(g.as_row() for g in games)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point: `python -m mhc_rankings.scraper SOURCE OUTPUT`."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("source", help="URL or saved HTML file of the completed-games page")
    ap.add_argument("output", type=Path, help="TSV file to write")
    ap.add_argument("--teams", type=Path, help="teams.toml used to check and normalize team names")
    ap.add_argument("--season-id", help="GameSheet season id for game links; read from the source URL when omitted")
    args = ap.parse_args(argv)
    try:
        season_id = args.season_id or season_id_from_url(args.source)
        games = load_games(args.source, season_id)
        if args.teams:
            games = canonicalize(games, load_roster(args.teams))
    except (ScrapeBlockedError, UnknownTeamError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_tsv(games, args.output)
    print(f"Wrote {len(games)} games to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
