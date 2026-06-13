"""
Bradley-Terry / Elo Ranking Engine

This module implements a hybrid ranking system combining the Elo rating system
with the Bradley-Terry model. 

1. **Bradley-Terry Model**: A probabilistic model that predicts the outcome of a paired
   comparison. Here, it is used to calculate the expected probability of Team A beating 
   Team B based on their current ratings. We use a standard logistic curve with a scale 
   factor of 400.
   
2. **Elo Update Mechanism**: After a game, the actual outcome is compared against the 
   expected probability. The team's rating is then adjusted. If a team performs better 
   than expected, they gain points; if worse, they lose points. 

3. **Margin of Victory Multiplier (MoVM)**: An optional enhancement that scales the rating
   exchange based on goal differential. It rewards blowouts but uses a logarithmic curve 
   to provide diminishing returns, preventing teams from endlessly running up the score.
   
The magnitude of the rating change is controlled by the `K-factor`. A higher K-factor 
makes the system more volatile (reactive to recent games), while a lower K-factor makes 
it more stable.
"""

import math
from typing import Any, Dict, List, Tuple

from .base import RankingEngine

class BTEloEngine(RankingEngine):
    """
    Implements a hybrid Bradley-Terry / Elo rating system.
    """
    
    def __init__(self, teams: List[str], initial_rating: float = 1500.0, k_factor: float = 32.0, use_movm: bool = False, max_gd: int = 4) -> None:
        self.teams = teams
        self.k_factor = k_factor
        self.use_movm = use_movm
        self.max_gd = max_gd
        self.ratings = {team: initial_rating for team in teams}
        self.initial_rating = initial_rating
        
        # Track total pre-game opponent ratings and games played to compute SOS
        self.opp_ratings_sum = {team: 0.0 for team in teams}
        self.games_played = {team: 0 for team in teams}

    def add_game(self, away: str, home: str, away_score: int, home_score: int, is_overtime: bool = False) -> None:
        """
        Process a single game, calculate expected win probabilities, and update ratings.
        """
        r_away = self.ratings[away]
        r_home = self.ratings[home]
        
        # Log pre-game opponent ratings for Strength of Schedule (SOS).
        # We record the opponent's rating *before* the game is played to reflect 
        # the challenge the team faced at that specific point in time.
        self.opp_ratings_sum[away] += r_home
        self.opp_ratings_sum[home] += r_away
        self.games_played[away] += 1
        self.games_played[home] += 1

        # Calculate Expected Probability of Winning (Bradley-Terry logistic curve)
        # Scale of 400 means a 400-point rating advantage translates to a 10x higher
        # likelihood of winning (approx 91% expected win probability).
        expected_away = 1.0 / (1.0 + 10.0 ** ((r_home - r_away) / 400.0))
        expected_home = 1.0 / (1.0 + 10.0 ** ((r_away - r_home) / 400.0))
        
        # Determine Actual Outcomes (1.0 for Regulation Win, 0.5 for Tie, 0.0 for Regulation Loss)
        # Overtime Outcomes: 0.667 for OT Win, 0.333 for OT Loss
        if is_overtime:
            win_val = 0.667
            loss_val = 0.333
        else:
            win_val = 1.0
            loss_val = 0.0
            
        if away_score > home_score:
            s_away, s_home = win_val, loss_val
            r_winner, r_loser = r_away, r_home
        elif home_score > away_score:
            s_away, s_home = loss_val, win_val
            r_winner, r_loser = r_home, r_away
        else:
            s_away, s_home = 0.5, 0.5
            r_winner, r_loser = r_home, r_away # Doesn't matter for a tie
            
        # Calculate Margin of Victory Multiplier (MoVM)
        movm = 1.0
        if self.use_movm and s_away != 0.5:
            # Cap the goal differential
            gd = min(abs(away_score - home_score), self.max_gd)
            rating_diff = r_winner - r_loser
            # MoVM formula adapted from standard power ranking methodologies
            movm = math.log(gd + 1) * (2.2 / (rating_diff * 0.001 + 2.2))
            
        # Update Ratings using the Elo formula: R_new = R_old + K * MoVM * (Actual - Expected)
        self.ratings[away] += self.k_factor * movm * (s_away - expected_away)
        self.ratings[home] += self.k_factor * movm * (s_home - expected_home)

    def solve(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Finalize and return the current ratings and the computed Strength of Schedule.
        """
        sos = {}
        for team in self.teams:
            games = self.games_played[team]
            sos[team] = self.opp_ratings_sum[team] / games if games > 0 else 0.0
            
        return dict(self.ratings), sos

    @property
    def details(self) -> Dict[str, Any]:
        """Return engine details for reporting."""
        return {
            "initial_rating": self.initial_rating,
            "k_factor": self.k_factor,
            "use_movm": self.use_movm,
            "max_gd": self.max_gd
        }
