from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from jinja2 import Environment, FileSystemLoader

from .models import TeamRecord
from .plotting import get_matplotlib_base64, get_plotly_html, get_team_gd_plot_html, get_team_rating_sos_plot_html

import pandas as pd

# Assuming this file is at src/mhc_rankings/reporting.py
# and the template is at src/mhc_rankings/templates/report.html
TEMPLATE_DIR = Path(__file__).parent / "templates"


def generate_html_report(
    date_str: str,
    rankings: List[TeamRecord],
    details: Any,
    teams: List[str],
    weekly_records: Dict[str, List[TeamRecord]],
    plot_engine: str,
    output_path: str | Path,
    df: pd.DataFrame,
    include_sos_plot: bool = False,
    method: str = "colley",
    use_movm:bool = False
) -> None:
    """
    Generates the final HTML report using Jinja2 and writes it to the output path.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("report.html")
    
    # Convert dataclasses to dicts for JSON serialization in the template
    formatted_rankings = [asdict(r) for r in rankings]
    
    all_weeks_data = {}
    for week, records in weekly_records.items():
        all_weeks_data[week] = [asdict(r) for r in records]
        
    sorted_weeks = sorted(all_weeks_data.keys())
    
    if method == "colley":
        title_method = "Colley" 
    else:
        title_method = "Bradley-Terry Elo"
        if use_movm:
            title_method += " (MOVM)"

    
    if plot_engine == "matplotlib":
        plot_data = get_matplotlib_base64(weekly_records, teams, f"MHC {title_method} Ratings Plot", f"{title_method} Rating", "rating")
        rank_plot_data = get_matplotlib_base64(weekly_records, teams, "Rankings Progress", "Rank", "rank")
        sos_plot_data = get_matplotlib_base64(weekly_records, teams, "Strength of Schedule Progress", "SOS", "sos") if include_sos_plot else None
    elif plot_engine == "plotly":
        plot_data = get_plotly_html(weekly_records, teams, f"MHC {title_method} Ratings Plot", f"{title_method} Rating", "rating")
        rank_plot_data = get_plotly_html(weekly_records, teams, "Rankings Progress", "Rank", "rank")
        sos_plot_data = get_plotly_html(weekly_records, teams, "Strength of Schedule Progress", "SOS", "sos") if include_sos_plot else None
    else:
        raise ValueError(f"Unknown plot engine: {plot_engine}")
        
    # Format the dataframe for display
    # Fill NA values with empty strings or reasonable defaults
    display_df = df.copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    display_df = display_df.fillna("")
    games_data = display_df.to_dict(orient="records")
        
    html_content = template.render(
        date=date_str,
        rankings=formatted_rankings,
        details=details,
        teams=teams,
        plot_engine=plot_engine,
        plot_data=plot_data,
        rank_plot_data=rank_plot_data,
        sos_plot_data=sos_plot_data,
        all_weeks_data=all_weeks_data,
        sorted_weeks=sorted_weeks,
        method=method,
        title_method=title_method,
        games_data=games_data
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

def generate_team_reports(
    date_str: str,
    rankings: list,
    team_logs: dict,
    plot_engine: str,
    output_path: str,
    method: str,
    use_movm: bool = False
) -> None:
    """Generates the HTML team reports."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("team_reports.html")
    
    team_names = sorted(team_logs.keys())
    
    teams_data = []
    for tname in team_names:
        record = next((r for r in rankings if r.team == tname), None)
        logs = team_logs[tname]
        
        plot_html = get_team_gd_plot_html(logs, tname, plot_engine)
        rating_sos_plot_html = get_team_rating_sos_plot_html(logs, tname, plot_engine)
        
        team_dict = {
            "name": tname,
            "rank": record.rank if record else "-",
            "rating": record.rating if record else 0.0,
            "w": record.wins + record.ot_wins if record else 0,
            "l": record.losses + record.ot_losses if record else 0,
            "t": record.t if record else 0,
            "sos": record.sos if record else 0.0,
            "gf": record.gf if record else 0,
            "ga": record.ga if record else 0,
            "logs": logs,
            "plot_html": plot_html,
            "rating_sos_plot_html": rating_sos_plot_html
        }
        teams_data.append(team_dict)
        
    if method == "colley":
        title_method = "Colley Matrix" 
    else:
        title_method = "Bradley-Terry Elo"
        if use_movm:
            title_method += " (MOVM)"
    
    html_out = template.render(
        date=date_str,
        team_names=team_names,
        teams_data=teams_data,
        method=method,
        title_method=title_method
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_out)
