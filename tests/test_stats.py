import pytest
import pandas as pd
from mhc_rankings.rankings_math import compute_final_rankings, compute_weekly_ratings

def test_ot_wins_and_losses_weekly_vs_final():
    """
    Test that Overtime Wins (OTW) and Overtime Losses (OTL) are correctly tracked 
    in both final standings and weekly progress. Ensure that the last week's stats
    exactly match the final output.
    """
    
    # Create mock game data focusing on OT scenarios
    data = {
        "Date": pd.to_datetime([
            "2026-01-01", 
            "2026-01-05", 
            "2026-01-10", 
            "2026-01-15"
        ]),
        "Away Team": ["Team A", "Team B", "Team C", "Team A"],
        "Home Team": ["Team B", "Team C", "Team A", "Team C"],
        "Score": ["3-2", "1-1", "4-5", "2-1"], # Last game is explicitly marked OT
        "Overtime": ["No", "OT", "Yes", "Yes"]
    }
    
    df = pd.DataFrame(data)
    
    # Parse scores
    def parse_score(score_str):
        parts = score_str.split("-")
        return pd.Series([int(parts[0]), int(parts[1])])
        
    df[["Away Score", "Home Score"]] = df["Score"].apply(parse_score)
    
    # 1. Compute Final Rankings
    final_rankings, _, final_teams = compute_final_rankings(df)
    final_dict = {rec.team: rec for rec in final_rankings}
    
    # Expected stats in final output:
    # Team A:
    #  Game 1: vs B (Away, 3-2, Reg) -> W
    #  Game 3: vs C (Home, 5-4, OT) -> OTW
    #  Game 4: vs C (Away, 2-1, OT) -> OTW
    #  Total: 1 W, 2 OTW, 0 L, 0 OTL, 0 T
    
    # Team B:
    #  Game 1: vs A (Home, 2-3, Reg) -> L
    #  Game 2: vs C (Away, 1-1, OT) -> T
    #  Total: 0 W, 0 OTW, 1 L, 0 OTL, 1 T
    
    # Team C:
    #  Game 2: vs B (Home, 1-1, OT) -> T
    #  Game 3: vs A (Away, 4-5, OT) -> OTL
    #  Game 4: vs A (Home, 1-2, OT) -> OTL
    #  Total: 0 W, 0 OTW, 0 L, 2 OTL, 1 T
    
    assert final_dict["Team A"].wins == 1
    assert final_dict["Team A"].ot_wins == 2
    assert final_dict["Team A"].losses == 0
    assert final_dict["Team A"].ot_losses == 0
    assert final_dict["Team A"].t == 0
    
    assert final_dict["Team B"].wins == 0
    assert final_dict["Team B"].ot_wins == 0
    assert final_dict["Team B"].losses == 1
    assert final_dict["Team B"].ot_losses == 0
    assert final_dict["Team B"].t == 1
    
    assert final_dict["Team C"].wins == 0
    assert final_dict["Team C"].ot_wins == 0
    assert final_dict["Team C"].losses == 0
    assert final_dict["Team C"].ot_losses == 2
    assert final_dict["Team C"].t == 1
    
    # 2. Compute Weekly Ratings
    weekly_records, weekly_teams = compute_weekly_ratings(df)
    
    # Find the last week
    sorted_weeks = sorted(weekly_records.keys())
    last_week_records = weekly_records[sorted_weeks[-1]]
    last_week_dict = {rec.team: rec for rec in last_week_records}
    
    # 3. Ensure last week's stats match final stats exactly
    for team in ["Team A", "Team B", "Team C"]:
        assert last_week_dict[team].wins == final_dict[team].wins
        assert last_week_dict[team].ot_wins == final_dict[team].ot_wins
        assert last_week_dict[team].losses == final_dict[team].losses
        assert last_week_dict[team].ot_losses == final_dict[team].ot_losses
        assert last_week_dict[team].t == final_dict[team].t
        assert last_week_dict[team].gf == final_dict[team].gf
        assert last_week_dict[team].ga == final_dict[team].ga


def test_last_game_uses_abbreviations_when_given() -> None:
    """Last Game shows the opponent's abbreviation when a map is supplied, else the full name."""
    from mhc_rankings.stats import StatsTracker

    tracker = StatsTracker(["Team A", "Team B"], {"Team B": "TB"})
    tracker.add_game("Team A", "Team B", 3, 1)
    assert tracker.stats["Team A"]["LastGame"] == "@ TB W 3-1"
    assert tracker.stats["Team B"]["LastGame"] == "vs Team A L 1-3"
