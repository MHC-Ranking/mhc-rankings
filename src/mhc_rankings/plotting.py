"""Interactive Plotly charts for the rankings page and the team reports."""

from typing import Any, Dict, List, Mapping

import plotly.graph_objects as go

from .models import TeamRecord

PLOT_HEIGHT = 623  # 15% shorter than the previous 733 pixels

_DASHES = ["solid", "dash", "dashdot", "longdash", "longdashdot", "dot"]
_MARKERS = [
    "circle", "square", "triangle-up", "diamond", "triangle-down", "triangle-left",
    "triangle-right", "pentagon", "star", "hexagon", "hexagon2", "cross", "x",
]
# Used for teams that have no color of their own.
_FALLBACK_COLORS = [
    "#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78", "#2ca02c", "#98df8a",
    "#d62728", "#ff9896", "#9467bd", "#c5b0d5", "#8c564b", "#c49c94",
    "#e377c2", "#f7b6d2", "#7f7f7f", "#c7c7c7", "#bcbd22", "#dbdb8d",
    "#17becf", "#9edae5",
]


def get_plotly_html(
    weekly_records: Dict[str, List[TeamRecord]],
    teams: List[str],
    title: str,
    ylabel: str,
    metric: str = "rating",
    colors: Mapping[str, str] | None = None,
    include_plotlyjs: bool = True,
) -> str:
    """
    Return an interactive line chart of `metric` for every team, one point per week, as an HTML div.

    `colors` maps team name to line color; teams without one get a palette color. Lines also differ
    in dash and marker so teams with similar colors stay distinguishable. The Plotly script is
    loaded from the CDN only when `include_plotlyjs` is true, so a page with several charts loads it once.
    """
    sorted_weeks = sorted(weekly_records.keys())
    if not sorted_weeks:
        return "<p>No data available for plotting.</p>"

    colors = colors or {}
    all_vals = [getattr(rec, metric) for week_data in weekly_records.values() for rec in week_data]
    min_y = min(all_vals) if all_vals else 0
    max_y = max(all_vals) if all_vals else 1
    y_padding = (max_y - min_y) * 0.05 if max_y > min_y else 0.1

    if metric == "rank":
        y_range = [max_y + 0.5, 0.5]  # Inverted Y-axis for ranks (1 at top)
        dtick = 1
    else:
        y_range = [min_y - y_padding, max_y + y_padding]
        dtick = None

    final_week = sorted_weeks[-1]
    final_data = {rec.team: getattr(rec, metric) for rec in weekly_records[final_week]}
    sorted_teams = sorted(teams, key=lambda team: final_data.get(team, 0.0), reverse=True)
    alphabetical_teams = sorted(teams)

    fig = go.Figure()

    for team in sorted_teams:
        team_idx = alphabetical_teams.index(team)
        values = [
            next((getattr(rec, metric) for rec in weekly_records[week] if rec.team == team), 0.0)
            for week in sorted_weeks
        ]
        fig.add_trace(go.Scatter(
            x=sorted_weeks,
            y=values,
            mode="lines+markers",
            name=team,
            line=dict(
                width=2,
                color=colors.get(team, _FALLBACK_COLORS[team_idx % len(_FALLBACK_COLORS)]),
                dash=_DASHES[team_idx % len(_DASHES)],
            ),
            marker=dict(symbol=_MARKERS[team_idx % len(_MARKERS)], size=8),
        ))

    # Dropdown menus for filtering teams
    top_6_teams = sorted_teams[:6]
    bottom_6_teams = sorted_teams[6:]

    dropdown_buttons = [
        dict(label="All Teams", method="update", args=[{"visible": [True] * len(sorted_teams)}]),
        dict(label="Top 6 Teams", method="update", args=[{"visible": [team in top_6_teams for team in sorted_teams]}]),
        dict(label="Bottom 6 Teams", method="update", args=[{"visible": [team in bottom_6_teams for team in sorted_teams]}]),
    ]
    for target_team in sorted_teams:
        dropdown_buttons.append(
            dict(label=target_team, method="update", args=[{"visible": [team == target_team for team in sorted_teams]}])
        )

    fig.update_layout(
        xaxis_title="Week",
        yaxis=dict(title=ylabel, range=y_range, dtick=dtick),
        legend_title="Teams",
        hovermode="x unified",
        template="plotly_white",
        updatemenus=[dict(
            type="dropdown",
            direction="down",
            x=0.0,
            xanchor="left",
            y=1.15,
            yanchor="top",
            buttons=dropdown_buttons,
        )],
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.01,
            itemclick="toggleothers",  # Clicking a legend item isolates it
            itemdoubleclick="toggle",
        ),
        xaxis=dict(type="category"),  # Weeks are labels, not numbers
        margin=dict(r=150, t=100),  # Room for the legend and dropdown
        height=PLOT_HEIGHT,
    )

    config = {
        "responsive": True,
        "toImageButtonOptions": {
            "format": "png",
            "filename": "mhc_plot",
            "height": 800,
            "width": 1200,
            "scale": 2,  # High resolution export
        },
        "displaylogo": False,
    }

    return fig.to_html(
        full_html=False,
        include_plotlyjs="cdn" if include_plotlyjs else False,
        config=config,
    )


def get_team_gd_plot_html(team_logs: List[Dict[str, Any]], team_name: str) -> str:
    """Return a bar chart of one team's goal differential in each game as an HTML div."""
    if not team_logs:
        return "<p>No data available.</p>"

    dates = [log["date"] for log in team_logs]
    gds = [log["gd"] for log in team_logs]
    opponents = [log["opponent"] for log in team_logs]
    colors = ["#2ca02c" if gd > 0 else "#d62728" if gd < 0 else "#7f7f7f" for gd in gds]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates,
        y=gds,
        marker_color=colors,
        text=gds,
        textposition="auto",
        hoverinfo="text",
        hovertext=[f"vs {opp}<br>GD: {gd}" for opp, gd in zip(opponents, gds)],
    ))
    fig.update_layout(
        title="Goal Differential by Game",
        xaxis_title="Date",
        yaxis_title="Goal Differential",
        template="plotly_white",
        height=280,
        margin=dict(l=50, r=30, t=45, b=40),
        xaxis=dict(type="category"),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def get_team_rating_sos_plot_html(team_logs: List[Dict[str, Any]], team_name: str) -> str:
    """Return a line chart of one team's rating and strength of schedule over time as an HTML div."""
    if not team_logs:
        return "<p>No data available.</p>"

    dates = [log["date"] for log in team_logs]
    ratings = [log["rating_post"] for log in team_logs]
    soses = [log["sos_post"] for log in team_logs]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=ratings,
        mode="lines+markers",
        name="Rating",
        line=dict(color="#1f77b4", width=2),
        marker=dict(symbol="circle", size=8),
    ))
    fig.add_trace(go.Scatter(
        x=dates,
        y=soses,
        mode="lines+markers",
        name="SOS",
        line=dict(color="#ff7f0e", width=2, dash="dash"),
        marker=dict(symbol="square", size=8),
    ))
    fig.update_layout(
        title="Rating and SOS over Time",
        xaxis_title="Date",
        yaxis_title="Value",
        template="plotly_white",
        height=280,
        margin=dict(l=50, r=30, t=45, b=40),
        xaxis=dict(type="category"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)
