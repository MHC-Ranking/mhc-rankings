from dataclasses import asdict
from datetime import date
from html import escape
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple
from urllib.parse import quote

from jinja2 import Environment, FileSystemLoader

from .models import TeamRecord
from .plotting import get_plotly_html, get_team_gd_plot_html, get_team_rating_sos_plot_html
from .rankings_math import WEEK_ZERO, game_week_ends
from .teams import Roster

import pandas as pd

# Assuming this file is at src/mhc_rankings/reporting.py
# and the template is at src/mhc_rankings/templates/report.html
TEMPLATE_DIR = Path(__file__).parent / "templates"
TEAM_REPORTS_FILE = "mhc_team_reports.html"
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


def league_name(roster: Roster | None) -> str:
    """Return the name used in report titles: "MHC Varsity" when the roster names its division, else "MHC"."""
    return f"MHC {roster.division}" if roster and roster.division else "MHC"


def team_anchor(name: str) -> str:
    """Return the id of a team's section on the team reports page."""
    return "team-" + name.replace(" ", "-")


def team_cell_html(name: str) -> str:
    """Return the table cell for a team: its name, linked (same tab) to its section of the team reports."""
    return f'<a href="{TEAM_REPORTS_FILE}#{escape(quote(team_anchor(name)))}">{escape(name)}</a>'


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


def _with_html_cells(record: TeamRecord) -> Dict[str, Any]:
    """Return `record` as a dict plus the ready-to-display `team_html` and `last_game_html` cells."""
    data = asdict(record)
    data["team_html"] = team_cell_html(record.team)
    data["last_game_html"] = link_html(record.last_game, record.last_game_url)
    return data


def week_option_label(week: str, week_end: date) -> str:
    """Return the week selector text, such as "Week 03 - Oct 25, 2026" (the Sunday that ends the week)."""
    return f"{week} - {week_end:%b} {week_end.day}, {week_end.year}"


def generate_html_report(
    date_str: str,
    details: Any,
    teams: List[str],
    weekly_records: Dict[str, List[TeamRecord]],
    output_path: str | Path,
    df: pd.DataFrame,
    roster: Roster | None = None
) -> None:
    """
    Generates the final HTML report using Jinja2 and writes it to the output path.

    The rankings table has one choice per game week (the last is the final ranking); Week 00, the
    0.5 starting point, appears only in the Ratings and Strength of Schedule charts.
    `roster` adds the schedule link and team-colored chart lines when given.
    """
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=True)
    template = env.get_template("report.html")

    game_weeks = {week: records for week, records in weekly_records.items() if week != WEEK_ZERO}
    all_weeks_data = {
        week: [_with_html_cells(r) for r in records] for week, records in game_weeks.items()
    }
    sorted_weeks = sorted(all_weeks_data.keys())
    week_options = [
        {"key": week, "label": week_option_label(week, week_end)}
        for week, week_end in game_week_ends(df).items()
    ]

    title_method = "Colley"

    line_colors = plot_line_colors(teams, roster)
    abbreviations = roster.abbreviations if roster else {}
    plot_data = get_plotly_html(
        weekly_records, teams, f"MHC {title_method} Ratings Plot", f"{title_method} Rating", "rating",
        line_colors, abbreviations=abbreviations,
    )
    rank_plot_data = get_plotly_html(
        game_weeks, teams, "Rankings Progress", "Rank", "rank", line_colors, include_plotlyjs=False,
        abbreviations=abbreviations,
    )
    sos_plot_data = get_plotly_html(
        weekly_records, teams, "Strength of Schedule Progress", "SOS", "sos", line_colors,
        include_plotlyjs=False, abbreviations=abbreviations,
    )

    # Format the dataframe for display
    # Fill NA values with empty strings or reasonable defaults
    display_df = df.copy()
    display_df["Date"] = display_df["Date"].dt.strftime("%Y-%m-%d")
    display_df = display_df.fillna("")
    games_data = display_df.to_dict(orient="records")

    matrix_labels = [abbreviations.get(team, team) for team in teams]
        
    html_content = template.render(
        date=date_str,
        league=league_name(roster),
        details=details,
        teams=teams,
        matrix_labels=matrix_labels,
        plot_data=plot_data,
        rank_plot_data=rank_plot_data,
        sos_plot_data=sos_plot_data,
        all_weeks_data=all_weeks_data,
        sorted_weeks=sorted_weeks,
        week_options=week_options,
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
    output_path: str,
    roster: Roster | None = None,
) -> None:
    """Generates the HTML team reports; `roster` adds each team's GameSheet page link and the division name."""
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template("team_reports.html")
    
    team_names = sorted(team_logs.keys())
    
    teams_data = []
    for tname in team_names:
        record = next((r for r in rankings if r.team == tname), None)
        logs = team_logs[tname]
        team = roster.find(tname) if roster else None
        
        plot_html = get_team_gd_plot_html(logs, tname)
        rating_sos_plot_html = get_team_rating_sos_plot_html(logs, tname)
        
        team_dict = {
            "name": tname,
            "anchor": team_anchor(tname),
            "gamesheet_url": safe_http_url(team.url) if team else "",
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
        league=league_name(roster),
        team_names=team_names,
        teams_data=teams_data,
        title_method=title_method
    )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_out)
