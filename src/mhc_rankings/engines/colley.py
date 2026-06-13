"""
Colley Matrix Ranking Engine

This module implements the Colley Matrix ranking system, a bias-free, mathematically 
robust method that models rankings as a system of linear equations: C * r = b.

- **Colley Matrix (C)**: Represents the schedule. Diagonal elements (C[i, i]) equal 2 plus 
  total games played. Off-diagonal elements (C[i, j]) equal the negative number of games 
  played between team i and team j.
- **Outcome Vector (b)**: Represents performance. b[i] = 1 + (Wins_i - Losses_i) / 2.
- **Solution (r)**: The resulting ratings vector.

Strength of Schedule (SOS) is computed as the average rating of a team's opponents.
"""

import numpy as np
from typing import Any, Dict, List, Tuple

from .base import RankingEngine

class ColleyEngine(RankingEngine):
    """Implements the Colley Matrix ranking system."""
    
    def __init__(self, teams: List[str]) -> None:
        self.teams = teams
        self.n_teams = len(teams)
        self.team_to_idx = {team: i for i, team in enumerate(teams)}
        
        # Initialize Colley Matrix (C). 
        # Diagonals start at 2 (Laplace smoothing factor).
        self.C = np.zeros((self.n_teams, self.n_teams))
        # Initialize the outcomes vector (b). Starts at 1.
        self.b = np.ones(self.n_teams)
        for i in range(self.n_teams):
            self.C[i, i] = 2
            
    def add_game(self, away: str, home: str, away_score: int, home_score: int, is_overtime: bool = False) -> None:
        """
        Process a single game result and incrementally update the C matrix and b vector.
        """
        i = self.team_to_idx[away]
        j = self.team_to_idx[home]
        
        # Update Colley Matrix (C) to reflect that these teams played each other
        # Increment the total games played on the diagonals
        self.C[i, i] += 1
        self.C[j, j] += 1
        # Decrement the cross-matchup off-diagonals
        self.C[i, j] -= 1
        self.C[j, i] -= 1
        
        # Update right-hand side vector (b) to reflect win/loss value
        # Base value is 0.5. Game value v dictates the addition: b += (v - 0.5)
        # Regulation: Win (1.0) -> +0.5, Loss (0.0) -> -0.5, Tie (0.5) -> 0.0
        # Overtime: Win (0.667) -> +0.167, Loss (0.333) -> -0.167, Tie (0.5) -> 0.0
        
        if is_overtime:
            win_val = 0.667 - 0.5  # 0.167
            loss_val = 0.333 - 0.5 # -0.167
        else:
            win_val = 1.0 - 0.5    # 0.5
            loss_val = 0.0 - 0.5   # -0.5
            
        if away_score > home_score:
            self.b[i] += win_val
            self.b[j] += loss_val
        elif home_score > away_score:
            self.b[j] += win_val
            self.b[i] += loss_val

    def solve(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Solves the system of linear equations C * r = b to determine ratings, 
        then calculates the Strength of Schedule (SOS) for each team.
        """
        # Solve C * r = b using NumPy's linear algebra solver
        r = np.linalg.solve(self.C, self.b)
        
        ratings = {}
        sos = {}
        for i, team in enumerate(self.teams):
            ratings[team] = float(r[i])
            
            # Compute Strength of Schedule (SOS)
            # t_games is total games played (diagonal element minus the base value of 2)
            t_games = self.C[i, i] - 2
            if t_games > 0:
                # SOS is the average rating of a team's opponents. 
                # By rearranging the Colley equation, the sum of opponent ratings 
                # equals C[i,i]*r[i] - b[i].
                sum_opp_ratings = self.C[i, i] * r[i] - self.b[i]
                sos[team] = float(sum_opp_ratings / t_games)
            else:
                sos[team] = 0.0
                
        return ratings, sos

    @property
    def details(self) -> np.ndarray:
        return self.C
