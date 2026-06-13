from dataclasses import dataclass, field

@dataclass
class TeamRecord:
    team: str
    rating: float = 0.0
    sos: float = 0.0
    wins: int = 0
    ot_wins: int = 0
    losses: int = 0
    ot_losses: int = 0
    t: int = 0
    gf: int = 0
    ga: int = 0
    rank: int = 0
    rank_change: int = 0
    last_game: str = ""
    win_pct: float = field(init=False)
    gd: int = field(init=False)

    def __post_init__(self):
        total = self.wins + self.ot_wins + self.losses + self.ot_losses + self.t
        # OTW = 0.667 win, OTL = 0.333 win, T = 0.5 win
        self.win_pct = (self.wins + (0.667 * self.ot_wins) + (0.333 * self.ot_losses) + (0.5 * self.t)) / total if total > 0 else 0.0
        self.gd = self.gf - self.ga
