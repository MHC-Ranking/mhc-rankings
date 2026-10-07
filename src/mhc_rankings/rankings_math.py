from typing import Any, Dict, List, Tuple
import pandas as pd

from .models import TeamRecord
from .stats import StatsTracker
from .engines.base import RankingEngine
from .engines.colley import ColleyEngine
from .engines.bt_elo import BTEloEngine

def get_teams(df: pd.DataFrame) -> List[str]:
    """Extracts a sorted list of unique teams from the games dataframe."""
    teams_set = set(df["Away Team"].dropna()) | set(df["Home Team"].dropna())
    return sorted(list(teams_set))

def get_engine(method: str, teams: List[str], **kwargs) -> RankingEngine:
    if method == "colley":
        return ColleyEngine(teams)
    elif method == "bt-elo":
        return BTEloEngine(teams, **kwargs)
    else:
        raise ValueError(f"Unknown ranking method: {method}")

def compute_final_rankings(df: pd.DataFrame, method: str, **engine_kwargs) -> Tuple[List[TeamRecord], Any, List[str]]:
    """
    Solves the rankings for the entire dataset based on the selected method.
    """
    teams = get_teams(df)
    engine = get_engine(method, teams, **engine_kwargs)
    stats = StatsTracker(teams)
    
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
        stats.add_game(away, home, away_score, home_score, is_overtime=ot)
        
    ratings, sos = engine.solve()
    records = stats.build_records(ratings, sos)
    
    # Assign final rank
    for idx, rec in enumerate(records):
        rec.rank = idx + 1
    
    return records, engine.details, teams

def compute_weekly_ratings(df: pd.DataFrame, method: str, **engine_kwargs) -> Tuple[Dict[str, List[TeamRecord]], List[str]]:
    """
    Computes the ratings and SOS iteratively over each week using the selected method.
    """
    valid_games = df.dropna(subset=["Away Score", "Home Score", "Date"]).copy()
    valid_games = valid_games.sort_values("Date")
    
    # Determine iso calendar weeks for valid games
    valid_games["ISO_Year"] = valid_games["Date"].dt.isocalendar().year
    valid_games["ISO_Week"] = valid_games["Date"].dt.isocalendar().week
    valid_games["Week_Key"] = valid_games.apply(lambda row: f"{row['ISO_Year']}-W{row['ISO_Week']:02d}", axis=1)
    
    teams = get_teams(df)
    engine = get_engine(method, teams, **engine_kwargs)
    stats = StatsTracker(teams)
    
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
            stats.add_game(away, home, away_score, home_score, is_overtime=ot)

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


def compute_team_game_logs(df: pd.DataFrame, method: str, **engine_kwargs) -> Dict[str, List[Dict[str, Any]]]:
    """
    Computes game-by-game logs for each team including rating changes and expectations.
    """
    valid_games = df.dropna(subset=["Away Score", "Home Score", "Date"]).copy()
    valid_games = valid_games.sort_values("Date")
    teams = get_teams(df)
    engine = get_engine(method, teams, **engine_kwargs)
    
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
            
        r_away_pre = engine.ratings[away] if method == "bt-elo" else None
        r_home_pre = engine.ratings[home] if method == "bt-elo" else None
        
        engine.add_game(away, home, away_score, home_score, is_overtime=ot)
        
        ratings, sos = engine.solve()
        
        exp_away, exp_home = None, None
        if method == "bt-elo":
            exp_away = 1.0 / (1.0 + 10.0 ** ((r_home_pre - r_away_pre) / 400.0))
            exp_home = 1.0 / (1.0 + 10.0 ** ((r_away_pre - r_home_pre) / 400.0))
            away_change = ratings[away] - r_away_pre
            home_change = ratings[home] - r_home_pre
        
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
            "rank_post": ranks[away],
            "opp_rating_pre": r_home_pre if method == "bt-elo" else None,
            "rating_change": away_change if method == "bt-elo" else None,
            "expected_win_prob": exp_away if method == "bt-elo" else None
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
            "rank_post": ranks[home],
            "opp_rating_pre": r_away_pre if method == "bt-elo" else None,
            "rating_change": home_change if method == "bt-elo" else None,
            "expected_win_prob": exp_home if method == "bt-elo" else None
        })

    return team_logs
