from typing import List
from .models import TeamRecord

def print_rankings_table(rankings: List[TeamRecord]) -> None:
    """
    Prints the calculated rankings table to the console.
    """
    print()
    print(f"{'Rank':<5} {'+/-':<4} {'Team':<25} {'Rating':<8} {'SOS':<8} {'Raw Win%':<10} {'W':<3} {'OTW':<3} {'T':<3} {'OTL':<3} {'L':<3} {'GF':<4} {'GA':<4} {'GD':<4} {'Last Game':<15}")
    print("-" * 124)
    
    for idx, rec in enumerate(rankings, 1):
        raw_change_str = f"▲{rec.rank_change}" if rec.rank_change > 0 else (f"▼{abs(rec.rank_change)}" if rec.rank_change < 0 else "-")
        pad = " " * max(0, 4 - len(raw_change_str))
        
        if rec.rank_change > 0:
            formatted_change = f"\033[32m{raw_change_str}\033[0m{pad}"
        elif rec.rank_change < 0:
            formatted_change = f"\033[31m{raw_change_str}\033[0m{pad}"
        else:
            formatted_change = f"{raw_change_str}{pad}"

        print(f"{idx:<5} {formatted_change} {rec.team:<25} {rec.rating:.4f}   {rec.sos:.4f}   {rec.win_pct:.3f}      {rec.wins:<3} {rec.ot_wins:<3} {rec.t:<3} {rec.ot_losses:<3} {rec.losses:<3} {rec.gf:<4} {rec.ga:<4} {rec.gd:<4} {rec.last_game}")
