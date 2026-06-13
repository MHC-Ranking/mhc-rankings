import pytest
import pandas as pd
from mhc_rankings.rankings_math import get_teams, get_engine, compute_final_rankings
from mhc_rankings.engines.colley import ColleyEngine
from mhc_rankings.engines.bt_elo import BTEloEngine

def test_get_teams():
    df = pd.DataFrame({
        "Away Team": ["Team B", "Team A"],
        "Home Team": ["Team C", "Team B"]
    })
    assert get_teams(df) == ["Team A", "Team B", "Team C"]

def test_get_engine():
    assert isinstance(get_engine("colley", ["A"]), ColleyEngine)
    assert isinstance(get_engine("bt-elo", ["A"]), BTEloEngine)
    with pytest.raises(ValueError):
        get_engine("unknown", ["A"])

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
    
    records, details, teams = compute_final_rankings(df, method="colley")
    
    assert teams == ["Team A", "Team B"]
    assert len(records) == 2
    
    assert records[0].team == "Team A"
    assert records[0].wins == 1
    assert records[0].rank == 1
    
    assert records[1].team == "Team B"
    assert records[1].losses == 1
    assert records[1].rank == 2