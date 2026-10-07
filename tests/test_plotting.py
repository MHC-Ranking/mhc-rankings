"""Tests for the Plotly charts."""

from mhc_rankings.models import TeamRecord
from mhc_rankings.plotting import (
    PLOT_HEIGHT,
    get_plotly_html,
    get_team_gd_plot_html,
    get_team_rating_sos_plot_html,
)

WEEKLY = {
    "2026-10-02": [TeamRecord(team="Alpha", rating=0.6, sos=0.5, rank=1), TeamRecord(team="Beta", rating=0.4, sos=0.5, rank=2)],
    "2026-10-09": [TeamRecord(team="Beta", rating=0.55, sos=0.5, rank=1), TeamRecord(team="Alpha", rating=0.45, sos=0.5, rank=2)],
}
LOGS = [
    {"date": "Oct 2", "gd": 2, "opponent": "Beta", "rating_post": 0.6, "sos_post": 0.5},
    {"date": "Oct 9", "gd": -1, "opponent": "Gamma", "rating_post": 0.55, "sos_post": 0.52},
]


def test_plot_height_is_15_percent_shorter() -> None:
    """The charts are 85% of their previous 733 pixel height and the chart uses that height."""
    assert PLOT_HEIGHT == round(733 * 0.85)
    assert f"height:{PLOT_HEIGHT}px" in get_plotly_html(WEEKLY, ["Alpha", "Beta"], "t", "Rating")


def test_chart_uses_team_colors_and_palette_fallback() -> None:
    """Teams with a color use it; teams without one get a palette color."""
    html = get_plotly_html(WEEKLY, ["Alpha", "Beta"], "t", "Rating", colors={"Alpha": "#123456"})
    assert "#123456" in html
    assert "#aec7e8" in html  # Beta's fallback (second palette color)


def test_chart_loads_plotly_script_only_when_asked() -> None:
    """A page with several charts can load the Plotly script once."""
    assert "cdn.plot.ly" in get_plotly_html(WEEKLY, ["Alpha", "Beta"], "t", "Rating")
    assert "cdn.plot.ly" not in get_plotly_html(WEEKLY, ["Alpha", "Beta"], "t", "Rating", include_plotlyjs=False)


def test_chart_with_no_weeks_says_so() -> None:
    """With no weekly data the chart is a plain message, not a failure."""
    assert "No data" in get_plotly_html({}, [], "t", "Rating")


def test_team_charts_and_empty_logs() -> None:
    """Team charts render for games and show a message for none."""
    assert "Goal Differential" in get_team_gd_plot_html(LOGS, "Alpha")
    assert "Rating and SOS" in get_team_rating_sos_plot_html(LOGS, "Alpha")
    assert "No data" in get_team_gd_plot_html([], "Alpha")
    assert "No data" in get_team_rating_sos_plot_html([], "Alpha")
