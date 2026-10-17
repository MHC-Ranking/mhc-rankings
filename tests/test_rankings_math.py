from datetime import date

import pandas as pd
import pytest

from mhc_rankings.engines.colley import ColleyEngine
from mhc_rankings.rankings_math import (
    WEEK_ZERO,
    compute_final_rankings,
    compute_team_game_logs,
    compute_weekly_ratings,
    game_week_ends,
    get_engine,
    get_teams,
)


def test_get_teams():
    df = pd.DataFrame({
        "Away Team": ["Team B", "Team A"],
        "Home Team": ["Team C", "Team B"]
    })
    assert get_teams(df) == ["Team A", "Team B", "Team C"]

def test_get_engine():
    assert isinstance(get_engine(["A"]), ColleyEngine)

def test_compute_final_rankings():
    data = {
        "Date": pd.to_datetime(["2026-01-01"]),
        "Away Team": ["Team A"],
        "Home Team": ["Team B"],
        "Away Score": [3],
        "Home Score": [1],
        "Overtime": ["No"]
    }
    df = pd.DataFrame(data)

    records, details, teams = compute_final_rankings(df)

    assert teams == ["Team A", "Team B"]
    assert len(records) == 2

    assert records[0].team == "Team A"
    assert records[0].wins == 1
    assert records[0].rank == 1

    assert records[1].team == "Team B"
    assert records[1].losses == 1
    assert records[1].rank == 2


def _games(dates: list[str]) -> pd.DataFrame:
    """Return one completed Team A (away) over Team B game per date, so each week has a clear result."""
    return pd.DataFrame({
        "Date": pd.to_datetime(dates),
        "Away Team": ["Team A"] * len(dates),
        "Home Team": ["Team B"] * len(dates),
        "Away Score": [3] * len(dates),
        "Home Score": [1] * len(dates),
        "Overtime": ["No"] * len(dates),
    })


def test_game_weeks_end_on_sunday_and_have_no_gaps() -> None:
    """Sunday games close their week, Monday starts a new one, and empty weeks are skipped in the numbering."""
    df = _games(["2026-10-02", "2026-10-04", "2026-10-05", "2026-10-20"])  # Fri, Sun, Mon, Tue
    assert game_week_ends(df) == {
        "Week 01": date(2026, 10, 4),
        "Week 02": date(2026, 10, 11),
        "Week 03": date(2026, 10, 25),
    }


def test_game_weeks_ignore_games_without_scores() -> None:
    """An unplayed game does not make its week a game week."""
    df = _games(["2026-10-02", "2026-10-20"])
    df.loc[1, "Away Score"] = None
    assert list(game_week_ends(df)) == ["Week 01"]


def test_weekly_ratings_start_at_week_zero_with_every_team_at_one_half() -> None:
    """Week 00 holds every team at rating 0.5 and SOS 0.5, followed by the game weeks in order."""
    weekly, teams = compute_weekly_ratings(_games(["2026-10-02", "2026-10-20"]))
    assert list(weekly) == [WEEK_ZERO, "Week 01", "Week 02"]
    assert teams == ["Team A", "Team B"]
    assert {r.team: (r.rating, r.sos, r.wins + r.losses) for r in weekly[WEEK_ZERO]} == {
        "Team A": (0.5, 0.5, 0),
        "Team B": (0.5, 0.5, 0),
    }


def test_week_one_has_no_rank_change_from_the_unordered_start() -> None:
    """Week 00 has no order, so Week 01 shows no movement and Week 02 compares with Week 01."""
    weekly, _ = compute_weekly_ratings(_games(["2026-10-02", "2026-10-20"]))
    assert [r.rank_change for r in weekly["Week 01"]] == [0, 0]
    assert [r.rank_change for r in weekly["Week 02"]] == [0, 0]
    assert [r.team for r in weekly["Week 02"]] == ["Team A", "Team B"]


def test_weekly_ratings_are_empty_without_completed_games() -> None:
    """With nothing played there is no Week 00 or any game week."""
    df = _games(["2026-10-02"])
    df["Away Score"] = None
    weekly, _ = compute_weekly_ratings(df)
    assert weekly == {}


def test_get_teams_includes_extra_teams_without_games() -> None:
    df = pd.DataFrame({"Away Team": ["Team B"], "Home Team": ["Team C"]})
    assert get_teams(df, ["Team D", "Team B", "Team A"]) == ["Team A", "Team B", "Team C", "Team D"]


def test_teams_without_games_are_ranked_at_the_starting_rating_and_sos() -> None:
    """An unplayed extra team has rating 0.5, SOS 0.5 and an empty record in the final and weekly results."""
    df = _games(["2026-10-02"])
    records, details, teams = compute_final_rankings(df, extra_teams=["Team Z"])
    unplayed = next(r for r in records if r.team == "Team Z")
    assert (unplayed.rating, unplayed.sos, unplayed.wins + unplayed.losses, unplayed.last_game) == (0.5, 0.5, 0, "")
    assert teams == ["Team A", "Team B", "Team Z"] and len(details) == 3

    weekly, _ = compute_weekly_ratings(df, extra_teams=["Team Z"])
    assert {r.team for r in weekly["Week 01"]} == {"Team A", "Team B", "Team Z"}

    logs = compute_team_game_logs(df, extra_teams=["Team Z"])
    assert logs["Team Z"] == [] and len(logs["Team A"]) == 1


def test_extra_teams_alone_give_a_week_zero_without_games() -> None:
    df = _games(["2026-10-02"]).iloc[0:0]
    weekly, teams = compute_weekly_ratings(df, extra_teams=["Team Y", "Team Z"])
    assert list(weekly) == [WEEK_ZERO] and teams == ["Team Y", "Team Z"]


def _tied_rating_games() -> pd.DataFrame:
    """Four teams that each won or lost one game, so winners tie on rating and so do losers."""
    return pd.DataFrame({
        "Date": pd.to_datetime(["2026-10-02"] * 2),
        "Away Team": ["Team A", "Team C"],
        "Home Team": ["Team B", "Team D"],
        "Away Score": [3, 5],
        "Home Score": [2, 0],
        "Overtime": ["No", "No"],
    })


def test_equal_ratings_are_ordered_by_goal_differential_then_goals_against_then_name() -> None:
    """Winners share a rating: the +5 team leads the +1 team; losers share one: -1 beats -5."""
    records, _, _ = compute_final_rankings(_tied_rating_games())
    assert [r.team for r in records] == ["Team C", "Team A", "Team B", "Team D"]
    assert [r.rank for r in records] == [1, 2, 3, 4]

    df = _tied_rating_games()
    df["Home Score"] = [0, 0]
    df["Away Score"] = [3, 3]  # A and C now match on rating, goal differential and goals against
    records, _, _ = compute_final_rankings(df)
    assert [r.team for r in records[:2]] == ["Team A", "Team C"]  # all equal: alphabetical


def test_fewer_goals_against_breaks_a_goal_differential_tie() -> None:
    df = _tied_rating_games()
    df["Away Score"] = [4, 3]  # A wins 4-1, C wins 3-0: both +3
    df["Home Score"] = [1, 0]
    records, _, _ = compute_final_rankings(df)
    assert [r.team for r in records[:2]] == ["Team C", "Team A"]


def test_weekly_tables_and_team_logs_use_the_same_tie_break() -> None:
    df = _tied_rating_games()
    weekly, _ = compute_weekly_ratings(df)
    assert [r.team for r in weekly["Week 01"]] == ["Team C", "Team A", "Team B", "Team D"]

    logs = compute_team_game_logs(df)  # ranks are as of each team's last game, which for C and D is the final one
    assert (logs["Team C"][-1]["rank_post"], logs["Team D"][-1]["rank_post"]) == (1, 4)
