"""Tests for the links and chart colors shown in the rankings report."""

from datetime import date
from pathlib import Path

from mhc_rankings.models import TeamRecord
from mhc_rankings.reporting import (
    _with_html_cells,
    generate_team_reports,
    link_html,
    plot_line_colors,
    safe_http_url,
    team_cell_html,
    week_option_label,
)
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


def test_team_cell_links_to_the_teams_report_section_in_the_same_tab() -> None:
    """A team name links to its section of the team reports page, with no new tab or color chips."""
    html = team_cell_html("Walt Whitman")
    assert html == '<a href="mhc_team_reports.html#team-Walt-Whitman">Walt Whitman</a>'
    assert "target" not in html
    assert "chip" not in html


def test_team_cell_escapes_unusual_names() -> None:
    """Markup and URL characters in a name cannot break out of the link."""
    html = team_cell_html('A & <B>')
    assert html == '<a href="mhc_team_reports.html#team-A-%26-%3CB%3E">A &amp; &lt;B&gt;</a>'


def test_week_option_label_shows_the_sunday_that_ends_the_week() -> None:
    """The selector text is the week label, a dash and the end date without a padded day."""
    assert week_option_label("Week 03", date(2026, 10, 25)) == "Week 03 - Oct 25, 2026"
    assert week_option_label("Week 01", date(2026, 10, 4)) == "Week 01 - Oct 4, 2026"


def test_team_reports_link_to_gamesheet_when_a_team_has_a_url(tmp_path: Path) -> None:
    """Each team report links to its GameSheet page, and teams without one get no link."""
    logs = {"Sherwood": [], "Other": []}
    out = tmp_path / "team_reports.html"
    generate_team_reports("Oct 9, 2026", [], logs, str(out), Roster([TEAM, Team("Other", "Oth", "", ("Red",))]))
    html = out.read_text(encoding="utf-8")
    assert html.count("Team page on GameSheet</a>") == 1
    assert 'href="https://example.com/team?a=1&amp;b=2"' in html
    assert 'id="team-Sherwood"' in html and 'href="#team-Sherwood"' in html


def test_record_cells_link_last_game_and_team() -> None:
    """A record's last game links to its game page and the team links to its report section."""
    stats = StatsTracker(["Sherwood", "Other"], {"Sherwood": "Sher", "Other": "Oth"})
    stats.add_game("Other", "Sherwood", 1, 3, game_url="https://example.com/games/7")
    record = next(r for r in stats.build_records({"Sherwood": 0.6, "Other": 0.4}, {}) if r.team == "Sherwood")
    data = _with_html_cells(record)
    assert data["last_game_url"] == "https://example.com/games/7"
    assert 'href="https://example.com/games/7"' in data["last_game_html"]
    assert data["last_game_html"].endswith(">vs Oth W 3-1</a>")
    assert data["team_html"].startswith('<a href="mhc_team_reports.html#team-Sherwood"')


def test_plot_line_colors_use_each_teams_first_hex_color() -> None:
    """Chart lines take the first team color; unknown teams, no roster and non-hex colors are skipped."""
    roster = Roster([TEAM, Team("Other", "Oth", "", ("Red",))])
    assert plot_line_colors(["Sherwood", "Other", "Nobody"], roster) == {"Sherwood": "#5b4fcf"}
    assert plot_line_colors(["Sherwood"], None) == {}


def test_record_cells_work_without_roster_or_game_url() -> None:
    """With no game URL the last game is plain escaped text and the team name is still linked."""
    data = _with_html_cells(TeamRecord(team="A <B>", last_game="@ C W 2-1"))
    assert data["team_html"].endswith(">A &lt;B&gt;</a>")
    assert data["last_game_html"] == "@ C W 2-1"
