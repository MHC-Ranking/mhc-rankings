from datetime import date
from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pandas as pd

from .engines.base import RankingEngine
from .engines.colley import ColleyEngine
from .models import TeamRecord
from .stats import StatsTracker, ranking_key

START_RATING = 0.5


def week_label(number: int) -> str:
    """Return the zero-padded label for game week `number`, such as "Week 03" ("Week 00" is the start)."""
    return f"Week {number:02d}"


WEEK_ZERO = week_label(0)


def _week_ends(dates: pd.Series) -> pd.Series:
    """Return the Sunday that ends the Monday-to-Sunday week of each date."""
    days = dates.dt.normalize()
    return days + pd.to_timedelta(6 - days.dt.weekday, unit="D")


def game_week_ends(df: pd.DataFrame) -> Dict[str, date]:
    """
    Map each game week's label to the Sunday that ends it, in order.

    A game week is a Monday-to-Sunday week with at least one completed game. Week 01 is the first
    such week and numbering has no gaps. The starting point, Week 00, is not included.
    """
    valid_games = df.dropna(subset=["Away Score", "Home Score", "Date"])
    ends = sorted(_week_ends(valid_games["Date"]).dt.date.unique())
    return {week_label(number): end for number, end in enumerate(ends, start=1)}

def get_teams(df: pd.DataFrame, extra_teams: Sequence[str] = ()) -> List[str]:
    """Extracts a sorted list of unique teams from the games dataframe plus `extra_teams` (teams that have not played)."""
    teams_set = set(df["Away Team"].dropna()) | set(df["Home Team"].dropna()) | set(extra_teams)
    return sorted(list(teams_set))


def _game_url(row: pd.Series) -> str:
    """Return the row's optional `Game URL`, or "" when the column or value is missing."""
    value = row.get("Game URL", "")
    return value if isinstance(value, str) else ""

def get_engine(teams: List[str]) -> RankingEngine:
    """Return the ranking engine for the season (Colley)."""
    return ColleyEngine(teams)

def compute_final_rankings(
    df: pd.DataFrame, abbreviations: Mapping[str, str] | None = None, extra_teams: Sequence[str] = ()
) -> Tuple[List[TeamRecord], Any, List[str]]:
    """
    Solves the rankings for the entire dataset.
    `abbreviations` maps team name to the short name used in the Last Game column.
    `extra_teams` are ranked too even if they have no games (at the starting rating).
    """
    teams = get_teams(df, extra_teams)
    engine = get_engine(teams)
    stats = StatsTracker(teams, abbreviations)

    valid_games = df.dropna(subset=["Away Score", "Home Score", "Date"]).copy()
    valid_games = valid_games.sort_values("Date")
    # for away, home, away_score, home_score in zip(
    #     valid_games["Away Team"], valid_games["Home Team"],
    #     valid_games["Away Score"], valid_games["Home Score"]
    # ):
    #     away_score, home_score = int(away_score), int(home_score)
    #     engine.add_game(away, home, away_score, home_score)
    #     stats.add_game(away, home, away_score, home_score)
    for irow, row in valid_games.iterrows():
        away = row["Away Team"]
        home = row["Home Team"]
        away_score = int(row["Away Score"])
        home_score = int(row["Home Score"])
        ot = row["Overtime"] in ["Yes", "True", "1", True, "OT", "ot"]
        if away_score == home_score:
            ot = True  # Treat ties as overtime games for rating purposes

        away_score, home_score = int(away_score), int(home_score)
        engine.add_game(away, home, away_score, home_score, is_overtime=ot)
        stats.add_game(away, home, away_score, home_score, is_overtime=ot, game_url=_game_url(row))

    ratings, sos = engine.solve()
    records = stats.build_records(ratings, sos)

    # Assign final rank
    for idx, rec in enumerate(records):
        rec.rank = idx + 1

    return records, engine.details, teams

def compute_weekly_ratings(
    df: pd.DataFrame, abbreviations: Mapping[str, str] | None = None, extra_teams: Sequence[str] = ()
) -> Tuple[Dict[str, List[TeamRecord]], List[str]]:
    """
    Computes the ratings and SOS iteratively over each game week.

    Keys are the labels from `game_week_ends` ("Week 01", ...), preceded by "Week 00", where every
    team starts at a rating and SOS of 0.5. Week 00 has no ranking order, so no rank changes are
    measured against it. Returns no weeks when there are no completed games, unless `extra_teams`
    are given: then every team is still ranked, so Week 00 alone is returned.
    """
    valid_games = df.dropna(subset=["Away Score", "Home Score", "Date"]).copy()
    valid_games = valid_games.sort_values("Date")

    week_by_end = {end: week for week, end in game_week_ends(df).items()}
    valid_games["Week_Key"] = _week_ends(valid_games["Date"]).dt.date.map(week_by_end)

    teams = get_teams(df, extra_teams)
    engine = get_engine(teams)
    stats = StatsTracker(teams, abbreviations)

    weekly_records: Dict[str, List[TeamRecord]] = {}
    if week_by_end or extra_teams:
        start_ratings, _ = engine.solve()  # no games yet, so every team is at the starting rating
        weekly_records[WEEK_ZERO] = stats.build_records(start_ratings, {team: START_RATING for team in teams})
        for idx, rec in enumerate(weekly_records[WEEK_ZERO]):
            rec.rank = idx + 1
    prev_ranks: Dict[str, int] = {}

    for week in week_by_end.values():
        week_games = valid_games[valid_games["Week_Key"] == week]

        for irow, row in week_games.iterrows():
            away = row["Away Team"]
            home = row["Home Team"]
            away_score = int(row["Away Score"])
            home_score = int(row["Home Score"])
            ot = row["Overtime"] in ["Yes", "True", "1", True, "OT", "ot"]
            if away_score == home_score:
                ot = True  # Treat ties as overtime games for rating purposes

            engine.add_game(away, home, away_score, home_score, is_overtime=ot)
            stats.add_game(away, home, away_score, home_score, is_overtime=ot, game_url=_game_url(row))

        ratings, sos = engine.solve()
        records = stats.build_records(ratings, sos)

        # Calculate rank changes
        for idx, rec in enumerate(records):
            current_rank = idx + 1
            rec.rank = current_rank
            rec.rank_change = prev_ranks.get(rec.team, current_rank) - current_rank

        weekly_records[week] = records
        prev_ranks = {rec.team: idx + 1 for idx, rec in enumerate(records)}

    return weekly_records, teams


def compute_team_game_logs(df: pd.DataFrame, extra_teams: Sequence[str] = ()) -> Dict[str, List[Dict[str, Any]]]:
    """
    Computes game-by-game logs for each team including the rating and rank after each game.
    `extra_teams` get an empty log if they have no games.
    """
    valid_games = df.dropna(subset=["Away Score", "Home Score", "Date"]).copy()
    valid_games = valid_games.sort_values("Date")
    teams = get_teams(df, extra_teams)
    engine = get_engine(teams)

    team_logs = {team: [] for team in teams}
    goals_for = {team: 0 for team in teams}
    goals_against = {team: 0 for team in teams}
    for irow, row in valid_games.iterrows():
        away = row["Away Team"]
        home = row["Home Team"]
        away_score = int(row["Away Score"])
        home_score = int(row["Home Score"])
        date_str = row["Date"].strftime("%Y-%m-%d") if hasattr(row["Date"], "strftime") else str(row["Date"])

        ot = row["Overtime"] in ["Yes", "True", "1", True, "OT", "ot"]
        if away_score == home_score:
            ot = True

        engine.add_game(away, home, away_score, home_score, is_overtime=ot)

        goals_for[away] += away_score
        goals_against[away] += home_score
        goals_for[home] += home_score
        goals_against[home] += away_score

        ratings, sos = engine.solve()

        order = sorted(
            teams,
            key=lambda t: ranking_key(ratings[t], goals_for[t] - goals_against[t], goals_against[t], t),
        )
        ranks = {t: i + 1 for i, t in enumerate(order)}

        team_logs[away].append({
            "date": date_str,
            "opponent": home,
            "is_home": False,
            "team_score": away_score,
            "opp_score": home_score,
            "gd": away_score - home_score,
            "ot": ot,
            "rating_post": ratings[away],
            "sos_post": sos[away],
            "rank_post": ranks[away]
        })

        team_logs[home].append({
            "date": date_str,
            "opponent": away,
            "is_home": True,
            "team_score": home_score,
            "opp_score": away_score,
            "gd": home_score - away_score,
            "ot": ot,
            "rating_post": ratings[home],
            "sos_post": sos[home],
            "rank_post": ranks[home]
        })

    return team_logs
