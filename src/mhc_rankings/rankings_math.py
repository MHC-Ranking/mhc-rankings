from typing import Any, Dict, List, Mapping, Tuple
import pandas as pd

from .models import TeamRecord
from .stats import StatsTracker
from .engines.base import RankingEngine
from .engines.colley import ColleyEngine

def get_teams(df: pd.DataFrame) -> List[str]:
    """Extracts a sorted list of unique teams from the games dataframe."""
    teams_set = set(df["Away Team"].dropna()) | set(df["Home Team"].dropna())
    return sorted(list(teams_set))


def _game_url(row: pd.Series) -> str:
    """Return the row's optional `Game URL`, or "" when the column or value is missing."""
    value = row.get("Game URL", "")
    return value if isinstance(value, str) else ""

def get_engine(teams: List[str]) -> RankingEngine:
    """Return the ranking engine for the season (Colley)."""
    return ColleyEngine(teams)

def compute_final_rankings(
    df: pd.DataFrame, abbreviations: Mapping[str, str] | None = None
) -> Tuple[List[TeamRecord], Any, List[str]]:
    """
    Solves the rankings for the entire dataset.
    `abbreviations` maps team name to the short name used in the Last Game column.
    """
    teams = get_teams(df)
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
    df: pd.DataFrame, abbreviations: Mapping[str, str] | None = None
) -> Tuple[Dict[str, List[TeamRecord]], List[str]]:
    """
    Computes the ratings and SOS iteratively over each week.
    """
    valid_games = df.dropna(subset=["Away Score", "Home Score", "Date"]).copy()
    valid_games = valid_games.sort_values("Date")
    
    # Determine iso calendar weeks for valid games
    valid_games["ISO_Year"] = valid_games["Date"].dt.isocalendar().year
    valid_games["ISO_Week"] = valid_games["Date"].dt.isocalendar().week
    valid_games["Week_Key"] = valid_games.apply(lambda row: f"{row['ISO_Year']}-W{row['ISO_Week']:02d}", axis=1)
    
    teams = get_teams(df)
    engine = get_engine(teams)
    stats = StatsTracker(teams, abbreviations)
    
    weekly_records: Dict[str, List[TeamRecord]] = {}
    sorted_weeks = sorted(valid_games["Week_Key"].unique())
    prev_ranks = {}
    
    for week in sorted_weeks:
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


def compute_team_game_logs(df: pd.DataFrame) -> Dict[str, List[Dict[str, Any]]]:
    """
    Computes game-by-game logs for each team including the rating and rank after each game.
    """
    valid_games = df.dropna(subset=["Away Score", "Home Score", "Date"]).copy()
    valid_games = valid_games.sort_values("Date")
    teams = get_teams(df)
    engine = get_engine(teams)
    
    team_logs = {team: [] for team in teams}
    
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
        
        ratings, sos = engine.solve()
        
        sorted_teams = sorted(ratings.items(), key=lambda x: x[1], reverse=True)
        ranks = {t: i + 1 for i, (t, r) in enumerate(sorted_teams)}
        
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
