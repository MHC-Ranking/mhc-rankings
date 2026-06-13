import csv
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from .models import TeamRecord


def load_games_data(file_path: str | Path) -> pd.DataFrame:
    """
    Loads game results from a TSV file into a pandas DataFrame.
    
    Args:
        file_path: Path to the TSV file.
        
    Returns:
        A pandas DataFrame containing the parsed game results.
    """
    df = pd.read_csv(file_path, sep="\t")
    
    # Ensure Date column is parsed as datetime
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"])
        
    # Parse scores
    def parse_score(score_str: str) -> pd.Series:
        parts = score_str.split("-")
        if len(parts) == 2:
            return pd.Series([int(parts[0]), int(parts[1])])
        return pd.Series([None, None])
        
    df[["Away Score", "Home Score"]] = df["Score"].apply(parse_score)
    
    df = df.sort_values("Date").reset_index(drop=True)
    return df


def get_latest_game_date(df: pd.DataFrame) -> str:
    """
    Finds the date of the most recent game in the dataset.
    
    Args:
        df: DataFrame containing game results.
        
    Returns:
        A formatted date string, e.g., 'May 30, 2026'.
    """
    if "Date" not in df.columns or df["Date"].isnull().all():
        return "Unknown Date"
    
    latest_date = df["Date"].max()
    return latest_date.strftime("%b %d, %Y")


def save_rankings_tsv(rankings: List[TeamRecord], output_path: str | Path) -> None:
    """
    Saves the computed rankings to a TSV file.
    """
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["Rank", "Team", "Rating", "SOS", "Raw Win%", "W", "OTW", "T", "OTL", "L", "GF", "GA", "GD"])
        for idx, rec in enumerate(rankings, 1):
            writer.writerow([idx, rec.team, f"{rec.rating:.4f}", f"{rec.sos:.4f}", f"{rec.win_pct:.3f}", rec.wins, rec.ot_wins, rec.t, rec.ot_losses, rec.losses, rec.gf, rec.ga, rec.gd])


def save_colley_matrix_tsv(C: Any, teams: List[str], output_path: str | Path) -> None:
    """
    Saves the Colley matrix to a TSV file.
    """
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["Team"] + teams)
        for i, team in enumerate(teams):
            row = [team] + [str(int(val)) if float(val).is_integer() else str(val) for val in C[i]]
            writer.writerow(row)


def save_weekly_ratings_tsv(weekly_records: Dict[str, List[TeamRecord]], teams: List[str], output_path: str | Path) -> None:
    """
    Saves the weekly ratings history to a TSV file.
    """
    sorted_weeks = sorted(weekly_records.keys())
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(["Week"] + teams)
        for week in sorted_weeks:
            # Map team to rating for easy lookup
            ratings = {rec.team: rec.rating for rec in weekly_records[week]}
            row = [week] + [f"{ratings.get(team, 0.0):.4f}" for team in teams]
            writer.writerow(row)
