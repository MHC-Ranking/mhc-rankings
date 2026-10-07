"""Tests for the links and chart colors shown in the rankings report."""

from mhc_rankings.models import TeamRecord
from mhc_rankings.reporting import _with_html_cells, link_html, plot_line_colors, safe_http_url, team_cell_html
from mhc_rankings.stats import StatsTracker
from mhc_rankings.teams import Roster, Team

TEAM = Team("Sherwood", "Sher", "https://example.com/team?a=1&b=2", ("#5b4fcf", "#ffffff"))


def test_safe_http_url_allows_only_web_links() -> None:
    """Only http(s) URLs may become links; scripts and blanks are dropped."""
    assert safe_http_url("https://example.com/x") == "https://example.com/x"
    assert safe_http_url("javascript:alert(1)") == ""
    assert safe_http_url("data:text/html,hi") == ""
    assert safe_http_url("") == ""


def test_link_html_escapes_text_and_url() -> None:
    """Link text and address are escaped so data cannot inject markup."""
    html = link_html('<b>@ A W 3-1</b>', 'https://example.com/g?a=1&b="2"')
    assert "<b>" not in html
    assert 'href="https://example.com/g?a=1&amp;b=&quot;2&quot;"' in html
    assert 'rel="noopener noreferrer"' in html


def test_link_html_is_plain_text_without_a_safe_url() -> None:
    """Without a usable URL the text is shown escaped and unlinked."""
    assert link_html("@ A W 3-1", "") == "@ A W 3-1"
    assert link_html("<i>x</i>", "javascript:alert(1)") == "&lt;i&gt;x&lt;/i&gt;"
    assert link_html("", "https://example.com") == ""


def test_team_cell_is_a_linked_name_without_color_chips() -> None:
    """A rostered team shows only its linked name."""
    html = team_cell_html("Sherwood", TEAM)
    assert html.startswith('<a href="https://example.com/team?a=1&amp;b=2"')
    assert "chip" not in html


def test_team_cell_without_url_is_unlinked_and_unknown_team_is_plain() -> None:
    """A blank team URL gives plain text; a team not in the roster is just its name."""
    assert team_cell_html("Sherwood", Team("Sherwood", "Sher", "", ("#5b4fcf",))) == "Sherwood"
    assert team_cell_html("A & B", None) == "A &amp; B"


def test_record_cells_link_last_game_and_team() -> None:
    """A record's last game links to its game page and the team links to its page."""
    stats = StatsTracker(["Sherwood", "Other"], {"Sherwood": "Sher", "Other": "Oth"})
    stats.add_game("Other", "Sherwood", 1, 3, game_url="https://example.com/games/7")
    record = next(r for r in stats.build_records({"Sherwood": 0.6, "Other": 0.4}, {}) if r.team == "Sherwood")
    data = _with_html_cells(record, Roster([TEAM]))
    assert data["last_game_url"] == "https://example.com/games/7"
    assert 'href="https://example.com/games/7"' in data["last_game_html"]
    assert data["last_game_html"].endswith(">vs Oth W 3-1</a>")
    assert "Sherwood</a>" in data["team_html"]


def test_plot_line_colors_use_each_teams_first_hex_color() -> None:
    """Chart lines take the first team color; unknown teams, no roster and non-hex colors are skipped."""
    roster = Roster([TEAM, Team("Other", "Oth", "", ("Red",))])
    assert plot_line_colors(["Sherwood", "Other", "Nobody"], roster) == {"Sherwood": "#5b4fcf"}
    assert plot_line_colors(["Sherwood"], None) == {}


def test_record_cells_work_without_roster_or_game_url() -> None:
    """With no roster and no game URL both cells are plain escaped text."""
    data = _with_html_cells(TeamRecord(team="A <B>", last_game="@ C W 2-1"), None)
    assert data["team_html"] == "A &lt;B&gt;"
    assert data["last_game_html"] == "@ C W 2-1"
