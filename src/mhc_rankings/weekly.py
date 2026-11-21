"""One-command weekly update: scrape results, rank the teams and write the index page.

Nothing is written unless the scrape succeeds and its results pass the checks (no repeated
games, valid scores, and every game already recorded is still present and unchanged), so a
blocked or partial scrape never replaces published results. The old games file is kept as
`~backup-<name>` beside it.
"""

import argparse
import csv
import shutil
import sys
import urllib.error
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from . import app
from .io import get_latest_game_date, load_games_data
from .scraper import (
    Game,
    ScrapeBlockedError,
    canonicalize,
    load_games,
    season_id_from_url,
    write_tsv,
)
from .teams import UnknownTeamError, load_roster

TEMPLATE_DIR = Path(__file__).parent / "templates"
BACKUP_PREFIX = "~backup-"


def load_recorded_games(games_file: Path) -> dict[str, dict[str, str]]:
    """Return the games already in `games_file` keyed by Game ID, or {} if it does not exist."""
    if not games_file.exists():
        return {}
    with games_file.open(encoding="utf-8", newline="") as f:
        return {row["Game ID"]: row for row in csv.DictReader(f, delimiter="\t")}


def _changed_games(games: list[Game], recorded: dict[str, dict[str, str]]) -> list[tuple[Game, dict[str, str]]]:
    """Return scraped games whose details differ from their recorded rows."""
    columns = ("Date", "Away Team", "Score", "Home Team", "Location", "Overtime")
    changed = []
    for game in games:
        previous = recorded.get(game.game_id)
        current = [game.date, game.away, f"{game.away_score}-{game.home_score}", game.home, game.location, game.overtime]
        if previous and current != [previous[column] for column in columns]:
            changed.append((game, previous))
    return sorted(changed, key=lambda pair: pair[0].game_id)


def check_games(games: list[Game], games_file: Path, allow_changed: bool = False) -> int:
    """Validate the scraped `games` against `games_file` and return how many are new.

    Raises:
        ValueError: If a game ID repeats, a score is negative, a team plays itself, or a
            game already recorded in `games_file` is missing or has different details when
            `allow_changed` is false.
    """
    ids = [g.game_id for g in games]
    repeated = sorted({i for i in ids if ids.count(i) > 1})
    if repeated:
        raise ValueError(f"The scrape repeats game IDs: {', '.join(repeated)}.")
    bad = [g.game_id for g in games if g.away_score < 0 or g.home_score < 0 or g.away == g.home]
    if bad:
        raise ValueError(f"The scrape has invalid scores or teams in: {', '.join(bad)}.")

    recorded = load_recorded_games(games_file)
    missing = sorted(set(recorded) - set(ids))
    if missing:
        raise ValueError(
            f"The scrape is missing {len(missing)} game(s) already recorded in {games_file} "
            f"(e.g. {missing[0]}). Nothing was changed; delete the file to rebuild it from the site."
        )
    changed = _changed_games(games, recorded)
    if changed and not allow_changed:
        raise ValueError(
            f"The scrape changes {len(changed)} game(s) already recorded in {games_file} "
            f"(e.g. {changed[0][0].game_id}). Nothing was changed; review the differences before updating."
        )
    return len(set(ids) - set(recorded))


def back_up_games_file(games_file: Path) -> Path | None:
    """Copy `games_file` to `~backup-<name>` beside it, replacing any earlier backup.

    Returns the backup path, or None when there is no file to back up.
    """
    if not games_file.exists():
        return None
    backup = games_file.with_name(BACKUP_PREFIX + games_file.name)
    shutil.copy2(games_file, backup)
    return backup


def write_index_page(output_dir: Path, title: str, latest_date: str, game_count: int) -> Path:
    """Write `index.html` linking the rankings and team reports in `output_dir`, and return its path."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    html = env.get_template("index.html").render(title=title, latest_date=latest_date, game_count=game_count)
    index = output_dir / "index.html"
    index.write_text(html, encoding="utf-8")
    return index


def main(argv: list[str] | None = None) -> int:
    """Scrape, rank and write the index page for one division; return 0 on success, 1 if nothing was published."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("games", type=Path, help="Games TSV to update; teams.toml (with games_url) must be beside it")
    ap.add_argument("--source", help="Completed-games page URL or saved HTML file; defaults to games_url in teams.toml")
    ap.add_argument("--output-dir", type=Path, help="Where to write the reports; defaults to 'rankings' beside the games file")
    ap.add_argument("--title", default="MHC Rankings", help="Heading for the index page")
    args = ap.parse_args(argv)

    teams_file = args.games.parent / "teams.toml"
    try:
        if not teams_file.exists():
            raise ValueError(f"{teams_file} not found.")
        roster = load_roster(teams_file)
        source = args.source or roster.games_url
        if not source:
            raise ValueError(f"No source given and {teams_file} has no games_url.")
        games = canonicalize(load_games(source, season_id_from_url(source)), roster)
        new_count = check_games(games, args.games, allow_changed=True)
        changed = _changed_games(games, load_recorded_games(args.games))
        if changed:
            print("The scrape has different details for these recorded games:")
            for game, previous in changed:
                print(
                    f"{game.game_id}\n"
                    f"  Recorded: {previous['Date']} | {previous['Away Team']} {previous['Score']} "
                    f"{previous['Home Team']} | {previous['Location']} | OT: {previous['Overtime'] or 'No'}\n"
                    f"  Scraped:  {game.date} | {game.away} {game.away_score}-{game.home_score} "
                    f"{game.home} | {game.location} | OT: {game.overtime or 'No'}"
                )
            try:
                answer = input("Update the recorded results with the scraped results? [y/N] ").strip().lower()
            except (EOFError, OSError):
                answer = ""
            if answer not in {"y", "yes"}:
                print("Update declined. Nothing was changed.", file=sys.stderr)
                return 1
    except (ScrapeBlockedError, UnknownTeamError, ValueError, urllib.error.URLError) as exc:
        print(f"error: {exc}\nNothing was changed.", file=sys.stderr)
        return 1

    backup = back_up_games_file(args.games)
    if backup:
        print(f"Backed up the games file to {backup}")
    write_tsv(games, args.games)
    print(f"Wrote {len(games)} games to {args.games} ({new_count} new)")

    output_dir = args.output_dir or args.games.parent / "rankings"
    app.main(["--input", str(args.games), "--output-dir", str(output_dir)])
    index = write_index_page(output_dir, args.title, get_latest_game_date(load_games_data(args.games)), len(games))
    print(f"Index page saved to {index}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
