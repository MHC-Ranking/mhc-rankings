import base64
import io
from typing import Dict, List

import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px

from .models import TeamRecord


def create_matplotlib_figure(weekly_records: Dict[str, List[TeamRecord]], teams: List[str], title: str, ylabel: str, metric: str = "rating") -> plt.Figure:
    """
    Creates a matplotlib figure for progress data over weeks.
    """
    sorted_weeks = sorted(weekly_records.keys())
    
    fig, ax = plt.subplots(figsize=(12, 8))
    
    line_styles = ["-", "--", "-.", (5, (10, 3)), (0, (5, 10)), (0, (1, 1))]
    markers = ["o", "s", "^", "D", "v", "<", ">", "p", "*", "h", "H", "+", "x"]
    colors = plt.cm.tab20.colors
    
    if not sorted_weeks:
        return fig
        
    final_week = sorted_weeks[-1]
    final_data = {rec.team: getattr(rec, metric) for rec in weekly_records[final_week]}
    sorted_teams = sorted(teams, key=lambda team: final_data.get(team, 0.0), reverse=True)
    alphabetical_teams = sorted(teams)
    
    for team in sorted_teams:
        team_idx = alphabetical_teams.index(team)
        ratings = []
        for week in sorted_weeks:
            val = next((getattr(rec, metric) for rec in weekly_records[week] if rec.team == team), 0.0)
            ratings.append(val)
            
        style = line_styles[team_idx % len(line_styles)]
        marker = markers[team_idx % len(markers)]
        color = colors[team_idx % len(colors)]
        
        ax.plot(sorted_weeks, ratings, linestyle=style, marker=marker, color=color, 
                label=team, linewidth=2, markersize=8)
                
    ax.set_title(title, fontsize=16)
    ax.set_xlabel("Week", fontsize=14)
    ax.set_ylabel(ylabel, fontsize=14)
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, linestyle="--", alpha=0.7)
    
    if metric == "rank":
        ax.invert_yaxis()
        ax.set_yticks(range(1, len(teams) + 1))
        
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    fig.tight_layout()
    
    return fig


def get_matplotlib_base64(weekly_records: Dict[str, List[TeamRecord]], teams: List[str], title: str, ylabel: str, metric: str = "rating") -> str:
    """
    Generates the matplotlib plot and returns it as a base64 encoded string for HTML embedding.
    """
    fig = create_matplotlib_figure(weekly_records, teams, title, ylabel, metric)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=300, bbox_inches="tight")
    plt.close(fig)
    
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return f"data:image/png;base64,{img_base64}"


def save_matplotlib_plot(weekly_records: Dict[str, List[TeamRecord]], teams: List[str], output_path: str, title: str, ylabel: str, metric: str = "rating") -> None:
    """
    Saves the matplotlib plot to disk as an image.
    """
    fig = create_matplotlib_figure(weekly_records, teams, title, ylabel, metric)
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def get_plotly_html(weekly_records: Dict[str, List[TeamRecord]], teams: List[str], title: str, ylabel: str, metric: str = "rating") -> str:
    """
    Generates an interactive Plotly plot and returns it as an HTML div string.
    """
    sorted_weeks = sorted(weekly_records.keys())
    if not sorted_weeks:
        return "<p>No data available for plotting.</p>"
        
    all_vals = [getattr(rec, metric) for week_data in weekly_records.values() for rec in week_data]
    min_y = min(all_vals) if all_vals else 0
    max_y = max(all_vals) if all_vals else 1
    y_padding = (max_y - min_y) * 0.05 if max_y > min_y else 0.1
    
    if metric == "rank":
        y_range = [max_y + 0.5, 0.5] # Inverted Y-axis for ranks (1 at top)
        dtick = 1
    else:
        y_range = [min_y - y_padding, max_y + y_padding]
        dtick = None
        
    final_week = sorted_weeks[-1]
    final_data = {rec.team: getattr(rec, metric) for rec in weekly_records[final_week]}
    sorted_teams = sorted(teams, key=lambda team: final_data.get(team, 0.0), reverse=True)
    alphabetical_teams = sorted(teams)
    
    fig = go.Figure()
    
    # Consistent markers and colors with Matplotlib implementation
    line_dash_styles = ["solid", "dash", "dashdot", "longdash", "longdashdot", "dot"]
    markers = ["circle", "square", "triangle-up", "diamond", "triangle-down", "triangle-left", "triangle-right", "pentagon", "star", "hexagon", "hexagon2", "cross", "x"]
    # Replicating plt.cm.tab20.colors in hex for Plotly
    colors = [
        '#1f77b4', '#aec7e8', '#ff7f0e', '#ffbb78', '#2ca02c', '#98df8a',
        '#d62728', '#ff9896', '#9467bd', '#c5b0d5', '#8c564b', '#c49c94',
        '#e377c2', '#f7b6d2', '#7f7f7f', '#c7c7c7', '#bcbd22', '#dbdb8d',
        '#17becf', '#9edae5'
    ]
    
    for team in sorted_teams:
        team_idx = alphabetical_teams.index(team)
        ratings = []
        for week in sorted_weeks:
            val = next((getattr(rec, metric) for rec in weekly_records[week] if rec.team == team), 0.0)
            ratings.append(val)
            
        dash_style = line_dash_styles[team_idx % len(line_dash_styles)]
        marker = markers[team_idx % len(markers)]
        color = colors[team_idx % len(colors)]
        
        fig.add_trace(go.Scatter(
            x=sorted_weeks,
            y=ratings,
            mode='lines+markers',
            name=team,
            line=dict(width=2, color=color, dash=dash_style),
            marker=dict(symbol=marker, size=8)
        ))
        
    # Dropdown menus for filtering teams
    top_6_teams = sorted_teams[:6]
    bottom_6_teams = sorted_teams[6:]
    
    dropdown_buttons = [
        dict(
            label="All Teams",
            method="update",
            args=[{"visible": [True] * len(sorted_teams)}]
        ),
        dict(
            label="Top 6 Teams",
            method="update",
            args=[{"visible": [team in top_6_teams for team in sorted_teams]}]
        ),
        dict(
            label="Bottom 6 Teams",
            method="update",
            args=[{"visible": [team in bottom_6_teams for team in sorted_teams]}]
        )
    ]
    
    # Add an individual option for each team
    for target_team in sorted_teams:
        dropdown_buttons.append(
            dict(
                label=target_team,
                method="update",
                args=[{"visible": [team == target_team for team in sorted_teams]}]
            )
        )
    
    updatemenus = [
        dict(
            type="dropdown",
            direction="down",
            x=0.0,
            xanchor="left",
            y=1.15,
            yanchor="top",
            buttons=dropdown_buttons
        )
    ]
        
    fig.update_layout(
        # title=title,
        xaxis_title="Week",
        yaxis=dict(title=ylabel, range=y_range, dtick=dtick),
        legend_title="Teams",
        hovermode="x unified",
        template="plotly_white",
        updatemenus=updatemenus,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=1.01,
            itemclick="toggleothers", # Clicking a legend item isolates it
            itemdoubleclick="toggle"
        ),
        xaxis=dict(
            type="category" # Ensure weeks are treated categorically
        ),
        margin=dict(r=150, t=100), # Make room for legend and dropdown
        width=1100,
        height=733
    )
    
    # Configure interactive options and high-res export
    config = {
        'toImageButtonOptions': {
            'format': 'png',
            'filename': 'mhc_plot',
            'height': 800,
            'width': 1200,
            'scale': 2 # High resolution export
        },
        'displaylogo': False
    }
    
    return fig.to_html(full_html=False, include_plotlyjs="cdn", config=config)


def get_team_gd_plot_html(team_logs: List[Dict[str, Any]], team_name: str, plot_engine: str = "plotly") -> str:
    """
    Generates a bar chart of goal differentials for a single team.
    """
    if not team_logs:
        return "<p>No data available.</p>"
        
    dates = [log["date"] for log in team_logs]
    gds = [log["gd"] for log in team_logs]
    opponents = [log["opponent"] for log in team_logs]
    colors = ['#2ca02c' if gd > 0 else '#d62728' if gd < 0 else '#7f7f7f' for gd in gds]
    
    if plot_engine == "plotly":
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=dates,
            y=gds,
            marker_color=colors,
            text=gds,
            textposition='auto',
            hoverinfo='text',
            hovertext=[f"vs {opp}<br>GD: {gd}" for opp, gd in zip(opponents, gds)]
        ))
        
        fig.update_layout(
            title=f"Goal Differential by Game",
            xaxis_title="Date",
            yaxis_title="Goal Differential",
            template="plotly_white",
            height=350,
            margin=dict(l=50, r=50, t=50, b=50),
            xaxis=dict(type='category')
        )
        return fig.to_html(full_html=False, include_plotlyjs=False)
    else:
        # Matplotlib fallback
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.bar(dates, gds, color=colors)
        ax.set_title(f"Goal Differential by Game")
        ax.set_xlabel("Date")
        ax.set_ylabel("Goal Differential")
        ax.axhline(0, color='black', linewidth=1)
        plt.xticks(rotation=45)
        fig.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f'<img src="data:image/png;base64,{img_base64}" alt="Goal Differential">'

def get_team_rating_sos_plot_html(team_logs: List[Dict[str, Any]], team_name: str, plot_engine: str = "plotly") -> str:
    """
    Generates a line graph of Rating and SOS over time for a single team.
    """
    if not team_logs:
        return "<p>No data available.</p>"
        
    dates = [log["date"] for log in team_logs]
    ratings = [log["rating_post"] for log in team_logs]
    soses = [log["sos_post"] for log in team_logs]
    
    if plot_engine == "plotly":
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=ratings,
            mode='lines+markers',
            name='Rating',
            line=dict(color='#1f77b4', width=2),
            marker=dict(symbol='circle', size=8)
        ))
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=soses,
            mode='lines+markers',
            name='SOS',
            line=dict(color='#ff7f0e', width=2, dash='dash'),
            marker=dict(symbol='square', size=8)
        ))
        
        fig.update_layout(
            title=f"Rating and SOS over Time",
            xaxis_title="Date",
            yaxis_title="Value",
            template="plotly_white",
            height=350,
            margin=dict(l=50, r=50, t=50, b=50),
            xaxis=dict(type='category'),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        return fig.to_html(full_html=False, include_plotlyjs=False)
    else:
        # Matplotlib fallback
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(dates, ratings, marker='o', label='Rating', color='#1f77b4', linewidth=2)
        ax.plot(dates, soses, marker='s', linestyle='--', label='SOS', color='#ff7f0e', linewidth=2)
        ax.set_title(f"Rating and SOS over Time")
        ax.set_xlabel("Date")
        ax.set_ylabel("Value")
        ax.legend()
        plt.xticks(rotation=45)
        fig.tight_layout()
        
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode("utf-8")
        return f'<img src="data:image/png;base64,{img_base64}" alt="Rating and SOS">'

