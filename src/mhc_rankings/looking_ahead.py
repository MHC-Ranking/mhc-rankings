"""Schedule-derived metrics and exact next-week outcome ranges."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import product
from statistics import mean
from typing import Sequence

import pandas as pd

from .models import TeamRecord
from .rankings_math import get_engine, get_teams
from .scraper import DATE_FORMAT, ScheduledGame
from .stats import ranking_key


@dataclass(frozen=True)
class TeamLookingAhead:
    """Current schedule metrics and the range across next-week outcomes."""

    sosf: float | None = None
    sosp: float | None = None
    rating_range: tuple[float, float] | None = None
    sos_range: tuple[float, float] | None = None
    rank_range: tuple[int, int] | None = None
    projection_date: str | None = None


def _game_date(game: ScheduledGame) -> datetime:
    return datetime.strptime(game.date, DATE_FORMAT)


def _is_overtime(value: object) -> bool:
    return value in ("Yes", "True", "1", True, "OT", "ot")


def _remaining_games(df: pd.DataFrame, scheduled_games: Sequence[ScheduledGame]) -> list[ScheduledGame]:
    played_ids = set()
    if "Game ID" in df.columns:
        played_ids = {str(value) for value in df["Game ID"].dropna() if str(value)}

    unique: dict[tuple[str, str, str, str], ScheduledGame] = {}
    for game in scheduled_games:
        if game.game_id and game.game_id in played_ids:
            continue
        key = (game.game_id, game.date, game.away, game.home)
        unique[key] = game
    return sorted(unique.values(), key=_game_date)


def _next_week(games: Sequence[ScheduledGame], played: pd.DataFrame) -> tuple[list[ScheduledGame], str | None]:
    if not games:
        return [], None

    candidates = list(games)
    if not played.empty:
        latest_played = pd.to_datetime(played["Date"]).max().date()
        candidates = [game for game in games if _game_date(game).date() >= latest_played]
    if not candidates:
        return [], None

    first_date = min(_game_date(game).date() for game in candidates)
    week_start = first_date - timedelta(days=first_date.weekday())
    week_games = [
        game for game in candidates
        if _game_date(game).date() - timedelta(days=_game_date(game).weekday()) == week_start
    ]
    return week_games, (week_start + timedelta(days=6)).isoformat()


def compute_looking_ahead(
    df: pd.DataFrame,
    scheduled_games: Sequence[ScheduledGame],
    current_rankings: Sequence[TeamRecord],
    extra_teams: Sequence[str] = (),
) -> dict[str, TeamLookingAhead]:
    """Compute SOSF/SOSP and exact rating, SOS, and rank ranges for the next scheduled week."""
    played = df.dropna(subset=["Away Score", "Home Score", "Date"]).copy()
    played = played.sort_values("Date")
    remaining = _remaining_games(df, scheduled_games)
    records = {record.team: record for record in current_rankings}
    teams = sorted(
        set(get_teams(df, extra_teams))
        | set(records)
        | {game.away for game in remaining}
        | {game.home for game in remaining}
    )
    current_ratings = {team: records[team].rating if team in records else 0.5 for team in teams}

    played_opponents: dict[str, list[str]] = {team: [] for team in teams}
    for _, row in played.iterrows():
        away, home = row["Away Team"], row["Home Team"]
        played_opponents[away].append(home)
        played_opponents[home].append(away)

    future_opponents: dict[str, list[str]] = {team: [] for team in teams}
    for game in remaining:
        future_opponents[game.away].append(game.home)
        future_opponents[game.home].append(game.away)

    next_week, projection_date = _next_week(remaining, played)
    result: dict[str, TeamLookingAhead] = {}
    rating_samples: dict[str, list[float]] = {team: [] for team in teams}
    sos_samples: dict[str, list[float]] = {team: [] for team in teams}
    rank_samples: dict[str, list[int]] = {team: [] for team in teams}

    if next_week:
        current_gd = {team: records[team].gd if team in records else 0 for team in teams}
        current_ga = {team: records[team].ga if team in records else 0 for team in teams}
        for away_wins in product((False, True), repeat=len(next_week)):
            engine = get_engine(teams)
            for _, row in played.iterrows():
                away_score = int(row["Away Score"])
                home_score = int(row["Home Score"])
                engine.add_game(
                    row["Away Team"], row["Home Team"], away_score, home_score,
                    is_overtime=_is_overtime(row.get("Overtime", "No")) or away_score == home_score,
                )
            for game, away_wins_game in zip(next_week, away_wins):
                engine.add_game(game.away, game.home, int(away_wins_game), int(not away_wins_game))

            ratings, soses = engine.solve()
            order = sorted(
                teams,
                key=lambda team: ranking_key(ratings[team], current_gd[team], current_ga[team], team),
            )
            ranks = {team: rank for rank, team in enumerate(order, start=1)}
            for team in teams:
                rating_samples[team].append(ratings[team])
                sos_samples[team].append(soses[team])
                rank_samples[team].append(ranks[team])

    for team in teams:
        future_ratings = [current_ratings[opponent] for opponent in future_opponents[team]]
        all_opponent_ratings = [
            current_ratings[opponent]
            for opponent in played_opponents[team] + future_opponents[team]
        ]
        result[team] = TeamLookingAhead(
            sosf=mean(future_ratings) if future_ratings else None,
            sosp=mean(all_opponent_ratings) if all_opponent_ratings else None,
            rating_range=(min(rating_samples[team]), max(rating_samples[team])) if rating_samples[team] else None,
            sos_range=(min(sos_samples[team]), max(sos_samples[team])) if sos_samples[team] else None,
            rank_range=(min(rank_samples[team]), max(rank_samples[team])) if rank_samples[team] else None,
            projection_date=projection_date if rating_samples[team] else None,
        )
    return result


def build_future_game_logs(
    df: pd.DataFrame,
    scheduled_games: Sequence[ScheduledGame],
    teams: Sequence[str],
) -> dict[str, list[dict[str, object]]]:
    """Build per-team future log rows with placeholders for every unknown game value."""
    team_logs = {team: [] for team in teams}
    for game in _remaining_games(df, scheduled_games):
        game_date = _game_date(game).date().isoformat()
        team_logs.setdefault(game.away, []).append({
            "date": game_date,
            "opponent": game.home,
            "is_home": False,
            "team_score": "-",
            "opp_score": "-",
            "gd": "-",
            "ot": False,
            "rating_post": "-",
            "rank_post": "-",
        })
        team_logs.setdefault(game.home, []).append({
            "date": game_date,
            "opponent": game.away,
            "is_home": True,
            "team_score": "-",
            "opp_score": "-",
            "gd": "-",
            "ot": False,
            "rating_post": "-",
            "rank_post": "-",
        })
    return team_logs