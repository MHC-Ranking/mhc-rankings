import pytest
import pandas as pd
import numpy as np
from mhc_rankings.io import (
    load_games_data, 
    get_latest_game_date, 
    save_rankings_tsv, 
    save_colley_matrix_tsv, 
    save_weekly_ratings_tsv
)
from mhc_rankings.models import TeamRecord

def test_load_games_data(tmp_path):
    tsv_content = (
        "Date\tAway Team\tHome Team\tScore\tOvertime\n"
        "2026-01-01\tTeam A\tTeam B\t3-2\tNo\n"
        "2026-01-05\tTeam C\tTeam D\t1-2\tYes\n"
    )
    p = tmp_path / "games.tsv"
    p.write_text(tsv_content)
    
    df = load_games_data(p)
    assert len(df) == 2
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])
    assert df["Away Score"].iloc[0] == 3
    assert df["Home Score"].iloc[0] == 2

def test_get_latest_game_date():
    df = pd.DataFrame({"Date": pd.to_datetime(["2025-10-01", "2026-02-15", "2026-01-10"])})
    assert get_latest_game_date(df) == "Feb 15, 2026"
    
    df_empty = pd.DataFrame({"Date": []})
    assert get_latest_game_date(df_empty) == "Unknown Date"

def test_save_rankings_tsv(tmp_path):
    rec = TeamRecord(team="Team A", rating=0.85, sos=0.6, wins=2, ot_wins=1, t=0, ot_losses=0, losses=1, gf=10, ga=5)
    p = tmp_path / "rankings.tsv"
    save_rankings_tsv([rec], p)
    
    content = p.read_text()
    assert "Rank\tTeam\tRating\tSOS\tRaw Win%\tW\tOTW\tT\tOTL\tL\tGF\tGA\tGD" in content
    assert "Team A\t0.8500\t0.6000" in content
    
def test_save_colley_matrix_tsv(tmp_path):
    C = np.array([[3, -1], [-1, 3]])
    teams = ["Team A", "Team B"]
    p = tmp_path / "matrix.tsv"
    save_colley_matrix_tsv(C, teams, p)
    
    content = p.read_text()
    assert "Team\tTeam A\tTeam B" in content
    assert "Team A\t3\t-1" in content
    
def test_save_weekly_ratings_tsv(tmp_path):
    rec1 = TeamRecord(team="Team A", rating=0.6)
    rec2 = TeamRecord(team="Team B", rating=0.4)
    records = {"2026-W01": [rec1, rec2]}
    teams = ["Team A", "Team B"]
    p = tmp_path / "weekly.tsv"
    save_weekly_ratings_tsv(records, teams, p)
    
    content = p.read_text()
    assert "Week\tTeam A\tTeam B" in content
    assert "2026-W01\t0.6000\t0.4000" in content