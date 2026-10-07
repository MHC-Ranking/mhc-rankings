from dataclasses import asdict
from html import escape
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

from jinja2 import Environment, FileSystemLoader

from .models import TeamRecord
from .plotting import get_plotly_html, get_team_gd_plot_html, get_team_rating_sos_plot_html
from .teams import Roster, Team

import pandas as pd

# Assuming this file is at src/mhc_rankings/reporting.py
# and the template is at src/mhc_rankings/templates/report.html
TEMPLATE_DIR = Path(__file__).parent / "templates"
_HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")


def safe_http_url(url: str) -> str:
    """Return `url` when it is an http(s) link, otherwise "" so it is never used as a link."""
    return url if url.startswith(("https://", "http://")) else ""


def link_html(text: str, url: str) -> str:
    """Return `text` escaped for HTML, wrapped in a new-tab link when `url` is a safe http(s) URL."""
    label = escape(text)
    safe = safe_http_url(url)
    if not label or not safe:
        return label
    return f'<a href="{escape(safe)}" target="_blank" rel="noopener noreferrer">{label}</a>'


def team_cell_html(name: str, team: Team | None) -> str:
    """Return the table cell for a team: its name, linked to its GameSheet page if it has one."""
    if team is None:
        return escape(name)
    return link_html(name, team.url)


def plot_line_colors(teams: List[str], roster: Roster | None) -> Dict[str, str]:
    """Return each rostered team's first color as its chart line color, skipping non-hex colors."""
    if roster is None:
        return {}
    found = ((name, roster.find(name)) for name in teams)
    return {
        name: team.colors[0]
        for name, team in found
        if team is not None and team.colors and _HEX_RE.fullmatch(team.colors[0])
    }


def _with_html_cells(record: TeamRecord, roster: Roster | None) -> Dict[str, Any]:
    """Return `record` as a dict plus the ready-to-display `team_html` and `last_game_html` cells."""
    data = asdict(record)
    data["team_html"] = team_cell_html(record.team, roster.find(record.team) if roster else None)
    data["last_game_html"] = link_html(record.last_game, record.last_game_url)
    return data


def generate_html_report(
    date_str: str,
    rankings: List[TeamRecord],
    details: Any,
    teams: List[str],
    weekly_records: Dict[str, List[TeamRecord]],
    output_path: str | Path,
    df: pd.DataFrame,
    roster: Roster | None = None
) -> None:
    """
    Generates the final HTML report using Jinja2 and writes it to the output path.
    `roster` adds team links, the schedule link and team-colored chart lines when given.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("report.html")
    
    # Convert dataclasses to dicts for JSON serialization in the template
    formatted_rankings = [_with_html_cells(r, roster) for r in rankings]
    
    all_weeks_data = {}
    for week, records in weekly_records.items():
        all_weeks_data[week] = [_with_html_cells(r, roster) for r in records]
        
    sorted_weeks = sorted(all_weeks_data.keys())
    
    title_method = "Colley"

    line_colors = plot_line_colors(teams, roster)
    plot_data = get_plotly_html(
        weekly_records, teams, f"MHC {title_method} Ratings Plot", f"{title_method} Rating", "rating", line_colors
    )
    rank_plot_data = get_plotly_html(
        weekly_records, teams, "Rankings Progress", "Rank", "rank", line_colors, include_plotlyjs=False
    )
    sos_plot_data = get_plotly_html(
        weekly_records, teams, "Strength of Schedule Progress", "SOS", "sos", line_colors, include_plotlyjs=False
    )

    # Format the dataframe for display
    # Fill NA values with empty strings or reasonable defaults
    display_df = df.copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    display_df = display_df.fillna("")
    games_data = display_df.to_dict(orient="records")

    abbreviations = roster.abbreviations if roster else {}
    matrix_labels = [abbreviations.get(team, team) for team in teams]
        
    html_content = template.render(
        date=date_str,
        rankings=formatted_rankings,
        details=details,
        teams=teams,
        matrix_labels=matrix_labels,
        plot_data=plot_data,
        rank_plot_data=rank_plot_data,
        sos_plot_data=sos_plot_data,
        all_weeks_data=all_weeks_data,
        sorted_weeks=sorted_weeks,
        title_method=title_method,
        games_data=games_data,
        schedule_url=safe_http_url(roster.schedule_url) if roster else ""
    )
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

def generate_team_reports(
    date_str: str,
    rankings: list,
    team_logs: dict,
    output_path: str
) -> None:
    """Generates the HTML team reports."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("team_reports.html")
    
    team_names = sorted(team_logs.keys())
    
    teams_data = []
    for tname in team_names:
        record = next((r for r in rankings if r.team == tname), None)
        logs = team_logs[tname]
        
        plot_html = get_team_gd_plot_html(logs, tname)
        rating_sos_plot_html = get_team_rating_sos_plot_html(logs, tname)
        
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
        
    title_method = "Colley Matrix"
    
    html_out = template.render(
        date=date_str,
        team_names=team_names,
        teams_data=teams_data,
        title_method=title_method
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_out)
