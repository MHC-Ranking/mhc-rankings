"""Tests for schedule metrics and next-week outcome ranges."""

import pandas as pd
import pytest

from mhc_rankings.looking_ahead import build_future_game_logs, compute_looking_ahead
from mhc_rankings.models import TeamRecord
from mhc_rankings.scraper import ScheduledGame


def _played_games() -> pd.DataFrame:
    return pd.DataFrame({
        "Date": pd.to_datetime(["2026-10-02"]),
        "Away Team": ["A"],
        "Home Team": ["B"],
        "Away Score": [3],
        "Home Score": [1],
        "Overtime": ["No"],
        "Game ID": ["G1"],
    })


def _current_records() -> list[TeamRecord]:
    return [
        TeamRecord(team="A", rating=0.7, gf=3, ga=1),
        TeamRecord(team="B", rating=0.3, gf=1, ga=3),
        TeamRecord(team="C", rating=0.5),
    ]


def _schedule() -> list[ScheduledGame]:
    return [
        ScheduledGame("Oct 9, 2026", "A", "B", "Rink 1", "G2"),
        ScheduledGame("Oct 10, 2026", "C", "A", "Rink 2", "G3"),
    ]


def test_sos_metrics_and_joint_outcome_ranges() -> None:
    result = compute_looking_ahead(_played_games(), _schedule(), _current_records())

    assert result["A"].sosf == pytest.approx((0.3 + 0.5) / 2)
    assert result["A"].sosp == pytest.approx((0.3 + 0.3 + 0.5) / 3)
    assert result["A"].rating_range == pytest.approx((0.4090909, 0.7272727))
    assert result["A"].sos_range == pytest.approx((0.3787879, 0.5151515))
    assert result["A"].rank_range == (1, 3)
    assert result["B"].rating_range == pytest.approx((0.2727273, 0.5454545))
    assert result["B"].rank_range == (2, 3)
    assert result["A"].projection_date == "2026-10-11"


def test_played_game_in_schedule_is_not_counted_as_future() -> None:
    schedule = [ScheduledGame("Oct 2, 2026", "A", "B", "Rink 1", "G1")]

    result = compute_looking_ahead(_played_games(), schedule, _current_records())

    assert result["A"].sosf is None
    assert result["A"].sosp == 0.3
    assert result["A"].rating_range is None


def test_projected_rating_ties_use_current_goal_differential() -> None:
    records = [
        TeamRecord(team="A", rating=0.5),
        TeamRecord(team="B", rating=0.5, gf=2),
        TeamRecord(team="C", rating=0.5),
        TeamRecord(team="D", rating=0.5),
    ]
    schedule = [ScheduledGame("Oct 9, 2026", "C", "D", "Rink 1", "G1")]

    empty_games = pd.DataFrame(columns=[
        "Date", "Away Team", "Home Team", "Away Score", "Home Score", "Overtime", "Game ID",
    ])
    result = compute_looking_ahead(empty_games, schedule, records)

    assert result["B"].rank_range == (2, 2)
    assert result["A"].rank_range == (3, 3)


def test_future_game_logs_have_placeholders_and_preserve_home_away() -> None:
    logs = build_future_game_logs(_played_games(), _schedule(), ["A", "B", "C"])

    assert logs["A"] == [
        {
            "date": "2026-10-09", "opponent": "B", "is_home": False,
            "team_score": "-", "opp_score": "-", "gd": "-", "ot": False,
            "rating_post": "-", "rank_post": "-",
        },
        {
            "date": "2026-10-10", "opponent": "C", "is_home": True,
            "team_score": "-", "opp_score": "-", "gd": "-", "ot": False,
            "rating_post": "-", "rank_post": "-",
        },
    ]