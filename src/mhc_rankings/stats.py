from typing import Dict, List, Mapping

from .models import TeamRecord

class StatsTracker:
    """Tracks base statistics (W, L, T, GF, GA, Last Game) for a set of teams."""
    
    def __init__(self, teams: List[str], abbreviations: Mapping[str, str] | None = None) -> None:
        """Start empty stats for `teams`; `abbreviations` maps team name to the short name shown in Last Game."""
        self.teams = teams
        self.abbreviations: Mapping[str, str] = abbreviations or {}
        self.stats = {team: {"W": 0, "OTW": 0, "L": 0, "OTL": 0, "T": 0, "GF": 0, "GA": 0, "LastGame": "", "LastGameUrl": ""} for team in teams}
        
    def add_game(
        self, away: str, home: str, away_score: int, home_score: int, is_overtime: bool = False, game_url: str = ""
    ) -> None:
        """Update cumulative stats based on a single game result; `game_url` links the game's page when known."""
        self.stats[away]["LastGameUrl"] = game_url
        self.stats[home]["LastGameUrl"] = game_url
        self.stats[away]["GF"] += away_score
        self.stats[away]["GA"] += home_score
        self.stats[home]["GF"] += home_score
        self.stats[home]["GA"] += away_score
        
        away_abbrev = self.abbreviations.get(away, away)
        home_abbrev = self.abbreviations.get(home, home)
        
        ot_str = " (OT)" if is_overtime else ""
        
        if away_score > home_score:
            if is_overtime:
                self.stats[away]["OTW"] += 1
                self.stats[home]["OTL"] += 1
            else:
                self.stats[away]["W"] += 1
                self.stats[home]["L"] += 1
            self.stats[away]["LastGame"] = f"@ {home_abbrev} W {away_score}-{home_score}{ot_str}"
            self.stats[home]["LastGame"] = f"vs {away_abbrev} L {home_score}-{away_score}{ot_str}"
        elif home_score > away_score:
            if is_overtime:
                self.stats[home]["OTW"] += 1
                self.stats[away]["OTL"] += 1
            else:
                self.stats[home]["W"] += 1
                self.stats[away]["L"] += 1
            self.stats[away]["LastGame"] = f"@ {home_abbrev} L {away_score}-{home_score}{ot_str}"
            self.stats[home]["LastGame"] = f"vs {away_abbrev} W {home_score}-{away_score}{ot_str}"
        else:
            self.stats[away]["T"] += 1
            self.stats[home]["T"] += 1
            self.stats[away]["LastGame"] = f"@ {home_abbrev} T {away_score}-{home_score}{ot_str}"
            self.stats[home]["LastGame"] = f"vs {away_abbrev} T {home_score}-{away_score}{ot_str}"

    def build_records(self, ratings: Dict[str, float], sos: Dict[str, float]) -> List[TeamRecord]:
        """Combines internal stats with external ratings and SOS into TeamRecord objects."""
        records = []
        for team in self.teams:
            st = self.stats[team]
            records.append(TeamRecord(
                team=team,
                rating=ratings.get(team, 0.0),
                sos=sos.get(team, 0.0),
                wins=st["W"],
                ot_wins=st["OTW"],
                losses=st["L"],
                ot_losses=st["OTL"],
                t=st["T"],
                gf=st["GF"],
                ga=st["GA"],
                last_game=st["LastGame"],
                last_game_url=st["LastGameUrl"],
            ))
            
        # Sort by rating, highest first
        records.sort(key=lambda x: x.rating, reverse=True)
        return records
