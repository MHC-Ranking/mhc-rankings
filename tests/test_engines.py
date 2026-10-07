import pytest
import numpy as np
from mhc_rankings.engines.colley import ColleyEngine


def test_colley_engine() -> None:
    """Colley matrix and ratings update correctly for regulation and overtime games."""
    teams = ["Team A", "Team B", "Team C"]
    engine = ColleyEngine(teams)

    # Initial state checks
    assert np.array_equal(engine.C, np.diag([2, 2, 2]))
    assert np.array_equal(engine.b, [1, 1, 1])

    # Add a regulation game: A beats B
    engine.add_game("Team A", "Team B", away_score=3, home_score=1, is_overtime=False)

    ratings, sos = engine.solve()

    # A should have higher rating than B. C should remain at 0.5
    assert ratings["Team A"] > ratings["Team B"]
    assert ratings["Team C"] == 0.5

    # Matrix details
    assert engine.C[0, 0] == 3  # A played 1 game + 2
    assert engine.C[1, 1] == 3  # B played 1 game + 2
    assert engine.C[0, 1] == -1  # A played B once
    assert engine.b[0] == 1.5  # 1 + 0.5
    assert engine.b[1] == 0.5  # 1 - 0.5

    # Overtime game: B beats C in OT
    engine.add_game("Team B", "Team C", away_score=2, home_score=1, is_overtime=True)

    # Win val for OT is 0.667 -> adds 0.167 (0.667 - 0.5) to b
    assert engine.b[1] == pytest.approx(0.667, abs=0.001)
    # Loss val for OT is 0.333 -> adds -0.167 (0.333 - 0.5) to b
    assert engine.b[2] == pytest.approx(0.833, abs=0.001)


def test_colley_engine_ratings_average_half() -> None:
    """Colley ratings average 0.5 across the league, even with ties and shutouts."""
    engine = ColleyEngine(["Team A", "Team B", "Team C"])
    engine.add_game("Team A", "Team B", away_score=3, home_score=3, is_overtime=True)
    engine.add_game("Team B", "Team C", away_score=5, home_score=0, is_overtime=False)
    ratings, _ = engine.solve()
    assert sum(ratings.values()) / 3 == pytest.approx(0.5)
    assert ratings["Team B"] > ratings["Team C"]


def test_colley_engine_no_games() -> None:
    """With no games played every team is rated 0.5."""
    ratings, _ = ColleyEngine(["Team A", "Team B"]).solve()
    assert ratings == {"Team A": 0.5, "Team B": 0.5}
