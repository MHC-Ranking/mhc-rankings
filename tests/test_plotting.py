"""Tests for the Plotly charts."""

from mhc_rankings.models import TeamRecord
from mhc_rankings.plotting import (
    LEGEND_MARGIN_MAX,
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


def _legend_order(html: str, names: list[str]) -> list[str]:
    """Return `names` sorted by where each first appears as a chart series name in `html`."""
    return sorted(names, key=lambda name: html.index(f'"name":"{name}"'))


def test_chart_legend_uses_abbreviations_but_hover_keeps_full_names() -> None:
    """The legend shows each team's short name, and the hover text still names the team in full."""
    html = get_plotly_html(WEEKLY, ["Alpha", "Beta"], "t", "Rating", abbreviations={"Alpha": "ALP", "Beta": "BET"})
    assert '"name":"ALP"' in html and '"name":"BET"' in html
    assert '"name":"Alpha"' not in html
    assert '"meta":"Alpha"' in html and "%{meta}" in html


def test_chart_legend_margin_shrinks_with_short_names_and_is_capped() -> None:
    """Short legend names leave a narrow right margin; long names keep at most the old 150 pixels."""
    short = get_plotly_html(WEEKLY, ["Alpha", "Beta"], "t", "Rating", abbreviations={"Alpha": "ALP", "Beta": "BET"})
    long = get_plotly_html(WEEKLY, ["Alpha", "Beta"], "t", "Rating", abbreviations={"Alpha": "A" * 40, "Beta": "B"})
    assert '"margin":{"r":81,' in short
    assert f'"margin":{{"r":{LEGEND_MARGIN_MAX},' in long


def test_rank_chart_legend_lists_rank_one_first_and_ratings_list_highest_first() -> None:
    """Rankings Progress lists the #1 team at the top of the legend; rating charts list the highest rating first."""
    rank_html = get_plotly_html(WEEKLY, ["Alpha", "Beta"], "t", "Rank", "rank")
    assert _legend_order(rank_html, ["Alpha", "Beta"]) == ["Beta", "Alpha"]  # Beta is rank 1 in the last week
    losing = {"2026-10-09": [TeamRecord(team="Alpha", rating=0.7, sos=0.5, rank=1), TeamRecord(team="Beta", rating=0.3, sos=0.5, rank=2)]}
    assert _legend_order(get_plotly_html(losing, ["Alpha", "Beta"], "t", "Rank", "rank"), ["Alpha", "Beta"]) == ["Alpha", "Beta"]
    assert _legend_order(get_plotly_html(losing, ["Alpha", "Beta"], "t", "Rating"), ["Alpha", "Beta"]) == ["Alpha", "Beta"]


def test_rank_chart_top_6_dropdown_shows_the_best_ranked_teams() -> None:
    """"Top 6 Teams" shows ranks 1-6 on the rankings chart, not the six lowest ranked."""
    teams = [f"T{n}" for n in range(1, 9)]
    final = {"2026-10-09": [TeamRecord(team=team, rating=1 - n / 10, sos=0.5, rank=n) for n, team in enumerate(teams, start=1)]}
    html = get_plotly_html(final, teams, "t", "Rank", "rank")
    top_six = html.index('"label":"Top 6 Teams"')
    assert '"visible":[true,true,true,true,true,true,false,false]' in html[top_six - 200 : top_six + 200]


def test_team_charts_resize_with_the_window() -> None:
    """Team report charts are responsive so they refit when a phone is rotated."""
    assert '"responsive": true' in get_team_gd_plot_html(LOGS, "Alpha")
    assert '"responsive": true' in get_team_rating_sos_plot_html(LOGS, "Alpha")


def test_team_charts_cannot_be_zoomed_or_panned() -> None:
    """Team report charts have no toolbar and fixed axes, but still show hover details."""
    for html in (get_team_gd_plot_html(LOGS, "Alpha"), get_team_rating_sos_plot_html(LOGS, "Alpha")):
        assert '"displayModeBar": false' in html
        assert '"scrollZoom": false' in html and '"doubleClick": false' in html
        assert '"dragmode":false' in html
        assert html.count('"fixedrange":true') == 2
