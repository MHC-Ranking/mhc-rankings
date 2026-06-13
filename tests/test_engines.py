import pytest
import numpy as np
from mhc_rankings.engines.colley import ColleyEngine
from mhc_rankings.engines.bt_elo import BTEloEngine

def test_colley_engine():
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
    assert engine.C[0, 0] == 3 # A played 1 game + 2
    assert engine.C[1, 1] == 3 # B played 1 game + 2
    assert engine.C[0, 1] == -1 # A played B once
    assert engine.b[0] == 1.5 # 1 + 0.5
    assert engine.b[1] == 0.5 # 1 - 0.5
    
    # Overtime game: B beats C in OT
    engine.add_game("Team B", "Team C", away_score=2, home_score=1, is_overtime=True)
    
    # Win val for OT is 0.667 -> adds 0.167 (0.667 - 0.5) to b
    # So b[1] was 0.5, now 0.5 + 0.167 = 0.667
    assert engine.b[1] == pytest.approx(0.667, abs=0.001)
    # Loss val for OT is 0.333 -> adds -0.167 (0.333 - 0.5) to b
    # So b[2] was 1.0, now 1.0 - 0.167 = 0.833
    assert engine.b[2] == pytest.approx(0.833, abs=0.001)

def test_bt_elo_engine():
    teams = ["Team A", "Team B", "Team C"]
    engine = BTEloEngine(teams, initial_rating=1500.0, k_factor=32.0, use_movm=False)
    
    # Game 1: A beats B
    engine.add_game("Team A", "Team B", away_score=4, home_score=2, is_overtime=False)
    ratings, sos = engine.solve()
    
    assert ratings["Team A"] > 1500.0
    assert ratings["Team B"] < 1500.0
    assert ratings["Team C"] == 1500.0
    
    assert sos["Team A"] == 1500.0
    assert sos["Team B"] == 1500.0
    
    # Test MoVM
    engine_movm = BTEloEngine(teams, initial_rating=1500.0, k_factor=32.0, use_movm=True, max_gd=4)
    engine_movm.add_game("Team A", "Team B", away_score=4, home_score=2, is_overtime=False)
    ratings_movm, _ = engine_movm.solve()
    
    # Rating change should be different due to MoVM
    assert ratings["Team A"] != ratings_movm["Team A"]
