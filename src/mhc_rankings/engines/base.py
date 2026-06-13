from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple

class RankingEngine(ABC):
    """Abstract base class for all ranking methodologies."""
    
    @abstractmethod
    def __init__(self, teams: List[str]) -> None:
        """Initialize the engine with a list of teams."""
        pass

    @abstractmethod
    def add_game(self, away: str, home: str, away_score: int, home_score: int, is_overtime: bool = False) -> None:
        """Process a single game result."""
        pass

    @abstractmethod
    def solve(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Compute and return ratings and SOS. 
        Returns:
            Tuple[Dict[str, float], Dict[str, float]]: (ratings_dict, sos_dict)
        """
        pass
    
    @property
    @abstractmethod
    def details(self) -> Any:
        """Return method-specific details (e.g., matrix, final Elo states) for reporting."""
        pass
