"""End-to-end test of the rankings command line."""

import re
from pathlib import Path

import pytest
from plotly.offline import get_plotlyjs_version

from mhc_rankings.app import main

GAMES = (
    "Date\tAway Team\tScore\tHome Team\tLocation\tGame ID\tOvertime\n"
    "Oct 2, 2026\tTeam A\t3-1\tTeam B\tRink 1\tMHC - 1\t\n"
    "Oct 9, 2026\tTeam B\t2-2\tTeam C\tRink 1\tMHC - 2\tOT\n"
    "Oct 16, 2026\tTeam C\t4-0\tTeam A\tRink 2\tMHC - 3\t\n"
)
TEAMS = "".join(
    f'[[team]]\nname = "Team {n}"\nabbreviation = "T{n}"\nurl = ""\ncolors = ["Red"]\n\n' for n in "ABC"
)


def test_cli_writes_reports_and_uses_abbreviations(tmp_path: Path) -> None:
    """The command takes the games file, reads teams.toml beside it, and writes one set of outputs."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert "Colley" in report
    assert "@ TA W 4-0" in report  # Team C's last game, with the opponent abbreviated
    assert (out / "mhc_team_reports.html").exists()


def test_cli_report_explains_colley_in_plain_language_first(tmp_path: Path) -> None:
    """The method section opens with the plain explanation and points table, then a closed Technical details block."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    plain = report.index("How the rankings work, in plain language")
    table = report.index('class="points-table"')
    technical = report.index("<summary>Technical details</summary>")
    assert plain < table < technical < report.index("\\vec{r}", technical)
    for label, share in [("Regulation win", "1.000"), ("Overtime win", "0.667"), ("Tie (decided in overtime)", "0.500"),
                         ("Overtime loss", "0.333"), ("Regulation loss", "0.000")]:
        assert f"<td>{label}</td><td>{share}</td>" in report
    assert "<details open" not in report[technical - 40 : technical]


def test_cli_report_lists_things_to_look_out_for_after_the_plain_explanation(tmp_path: Path) -> None:
    """The cautions about strength of schedule follow the plain explanation and come before Technical details."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    example = report.index("<em>Example:</em>")
    cautions = report.index("Things to Look Out For")
    technical = report.index("<summary>Technical details</summary>")
    assert example < cautions < technical
    assert report[cautions:technical].count("<li>") == 3
    assert "their rating can change even if they don't play a game" in report

def test_cli_game_matrix_uses_abbreviations_and_game_counts(tmp_path: Path) -> None:
    """The Game Matrix replaces Colley Details, labels rows and columns with abbreviations and counts meetings."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert "<summary>Game Matrix</summary>" in report
    assert "Colley Details" not in report
    assert '<th scope="row" title="Team A">TA</th>' in report
    assert '<th scope="col" title="Team B">TB</th>' in report
    assert '<td class="g1" title="Team A vs Team B">1</td>' in report  # one meeting, shown as a positive count
    assert '<td class="self">' in report


def test_cli_game_matrix_falls_back_to_full_names_without_roster(tmp_path: Path) -> None:
    """With no teams.toml the Game Matrix is labelled with full team names."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert '<th scope="row" title="Team A">Team A</th>' in report


def test_cli_rejects_removed_method_option(tmp_path: Path) -> None:
    """Colley is the only method, so --method no longer exists."""
    with pytest.raises(SystemExit):
        main(["--input", str(tmp_path / "games.tsv"), "--method", "colley"])


def test_cli_rejects_removed_plot_engine_option(tmp_path: Path) -> None:
    """Plotly is the only chart library, so --plot-engine no longer exists."""
    with pytest.raises(SystemExit):
        main(["--input", str(tmp_path / "games.tsv"), "--plot-engine", "matplotlib"])


def test_cli_report_has_accessible_chart_tabs_and_team_colors(tmp_path: Path) -> None:
    """The report shows three keyboard-navigable chart tabs, colored by team, and writes no PNG files."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS.replace('"Red"', '"#abcdef"'), encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out)])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert report.count('role="tab" id=') == 3
    assert report.count('role="tabpanel"') == 3
    assert report.count('aria-selected="true" tabindex="0"') == 1
    assert report.count("cdn.plot.ly") == 1
    assert "#abcdef" in report
    assert not list(out.glob("*.png"))


def test_cli_reports_missing_input_file(tmp_path: Path) -> None:
    """A missing games file exits with an error instead of a traceback."""
    with pytest.raises(SystemExit) as excinfo:
        main(["--input", str(tmp_path / "missing.tsv")])
    assert excinfo.value.code == 1


def test_cli_links_games_teams_and_schedule(tmp_path: Path) -> None:
    """Game URLs, team URLs and the schedule link from the inputs appear in the report."""
    games = tmp_path / "games.tsv"
    games.write_text(
        GAMES.replace("Overtime\n", "Overtime\tGame URL\n")
        .replace("\t\n", "\thttps://example.com/games/1\n", 1)
        .replace("OT\n", "OT\thttps://example.com/games/2\n")
        .replace("Rink 2\tMHC - 3\t\n", "Rink 2\tMHC - 3\t\t\n"),
        encoding="utf-8",
    )
    (tmp_path / "teams.toml").write_text(
        'schedule_url = "https://example.com/schedule"\n\n'
        + TEAMS.replace('url = ""', 'url = "https://example.com/team"'),
        encoding="utf-8",
    )
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert 'href="https://example.com/schedule"' in report
    assert "https://example.com/games/1" in report
    assert "https://example.com/team" in (out / "mhc_team_reports.html").read_text(encoding="utf-8")


def test_cli_selector_lists_game_weeks_with_sunday_dates_and_no_final_option(tmp_path: Path) -> None:
    """The table offers Week 01 onward, each with the Sunday that ends it; Week 00 and Final Rankings are gone."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out)])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert '<option value="Week 01">Week 01 - Oct 4, 2026</option>' in report
    assert '<option value="Week 02">Week 02 - Oct 11, 2026</option>' in report
    assert '<option value="Week 03">Week 03 - Oct 18, 2026</option>' in report
    assert '<option value="Week 00"' not in report
    assert "Final" not in report


def test_cli_week_zero_is_in_the_weekly_file_and_the_rating_charts_but_not_rank_progress(tmp_path: Path) -> None:
    """Week 00 (every team at 0.5) is saved and charted for ratings and SOS, but not for rankings progress."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out)])

    rows = (out / "weekly_ratings_output.tsv").read_text(encoding="utf-8").splitlines()
    assert [row.split("\t")[0] for row in rows] == ["Week", "Week 00", "Week 01", "Week 02", "Week 03"]
    assert rows[1].split("\t")[1:] == ["0.5000"] * 3
    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert report.count('"x":["Week 00","Week 01","Week 02","Week 03"]') == 6  # 3 teams in each of 2 charts
    assert report.count('"x":["Week 01","Week 02","Week 03"]') == 3  # rankings progress


def test_cli_team_names_link_to_team_reports_and_reports_link_to_gamesheet(tmp_path: Path) -> None:
    """The table links each team to its team report section; the team report links out to GameSheet."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(
        TEAMS.replace('url = ""', 'url = "https://example.com/team"'), encoding="utf-8"
    )
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert 'href=\\"mhc_team_reports.html#team-Team-A\\"' in report  # inside the embedded JSON
    assert 'href=\\"https://example.com/team\\"' not in report
    teams_page = (out / "mhc_team_reports.html").read_text(encoding="utf-8")
    assert 'id="team-Team-A"' in teams_page
    assert teams_page.count('href="https://example.com/team"') == 3



def test_cli_titles_name_the_division_and_date(tmp_path: Path) -> None:
    """Both reports are titled "MHC <division> Rankings/Team Reports - <date>" using the division in teams.toml."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text('division = "JV"\n\n' + TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    teams_page = (out / "mhc_team_reports.html").read_text(encoding="utf-8")
    assert "<h1>MHC JV Rankings - Oct 16, 2026</h1>" in report
    assert "<title>MHC JV Rankings - Oct 16, 2026</title>" in report
    assert "<h1>MHC JV Team Reports - Oct 16, 2026</h1>" in teams_page
    assert "<title>MHC JV Team Reports - Oct 16, 2026</title>" in teams_page


def test_cli_rankings_table_styles_are_scoped_to_the_rankings_table(tmp_path: Path) -> None:
    """The compact one-line row styling applies only to the rankings table, which scrolls sideways when narrow."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert '<div class="table-scroll">\n        <table class="rankings-table">' in report
    assert ".rankings-table {\n            font-size: 0.9em;" in report
    assert "white-space: nowrap" in report
    assert report.count('class="rankings-table"') == 1


def test_cli_titles_omit_the_division_when_not_named(tmp_path: Path) -> None:
    """Without a division the titles read "MHC Rankings" and "MHC Team Reports"."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    assert "<h1>MHC Rankings - Oct 16, 2026</h1>" in (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert "<h1>MHC Team Reports - Oct 16, 2026</h1>" in (out / "mhc_team_reports.html").read_text(encoding="utf-8")


def test_cli_team_log_ends_with_the_current_standing_that_matches_the_header(tmp_path: Path) -> None:
    """A team's log shows its rating as of each game, then a Current standing row equal to the header and rankings."""
    games = tmp_path / "games.tsv"
    games.write_text(  # Team B's last game is Oct 2, then Team C beats Team A, which moves Team B's rating
        "Date\tAway Team\tScore\tHome Team\tLocation\tGame ID\tOvertime\n"
        "Oct 2, 2026\tTeam A\t3-1\tTeam B\tRink 1\tMHC - 1\t\n"
        "Oct 9, 2026\tTeam C\t4-0\tTeam A\tRink 2\tMHC - 2\t\n",
        encoding="utf-8",
    )
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    page = (out / "mhc_team_reports.html").read_text(encoding="utf-8")
    section = page[page.index('id="team-Team-B"') : page.index('id="team-Team-C"')]
    header_rating = re.search(r'stat-value">(\d\.\d{4})</div>\s*<div class="stat-label">Current Rating', section)
    ratings = re.findall(r"<td>(\d\.\d{4})</td>", section)
    assert header_rating is not None
    assert "Rating After Game" in section and "Rank After Game" in section
    assert 'class="current-row"' in section and "Current standing" in section
    assert ratings[-1] == header_rating.group(1)  # the Current standing row
    assert ratings[-2] != ratings[-1]


def test_cli_pages_have_phone_layouts_and_the_rankings_charts_shrink_their_legends(tmp_path: Path) -> None:
    """Every page carries phone-only styles, the rankings table can scroll, and the legend uses team abbreviations."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out), "--skip-raw"])

    report = (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    teams_page = (out / "mhc_team_reports.html").read_text(encoding="utf-8")
    assert "@media (max-width: 700px)" in report
    assert "PHONE_LAYOUT" in report
    assert '"name":"TA"' in report and '"name":"Team A"' not in report
    assert "@media (max-width: 800px)" in teams_page
    assert 'id="teamToggle"' in teams_page and 'id="teamLinks"' in teams_page
    assert f"https://cdn.plot.ly/plotly-{get_plotlyjs_version()}.min.js" in teams_page
    assert "plotly-latest" not in teams_page
    assert '<div class="table-scroll">\n            <table>' in teams_page


def test_cli_ranks_roster_teams_that_have_not_played(tmp_path: Path) -> None:
    """A team in teams.toml with no games still appears in the rankings, team reports and raw files."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES, encoding="utf-8")
    (tmp_path / "teams.toml").write_text(
        TEAMS + '[[team]]\nname = "Team D"\nabbreviation = "TD"\nurl = ""\ncolors = ["Red"]\n', encoding="utf-8"
    )
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out)])

    assert "\tTeam D\t0.5000\t0.5000\t" in (out / "rankings_output.tsv").read_text(encoding="utf-8")
    assert 'id="team-Team-D"' in (out / "mhc_team_reports.html").read_text(encoding="utf-8")
    assert '"team":"Team D"' in (out / "mhc_rankings_report.html").read_text(encoding="utf-8").replace(": ", ":")


def test_cli_resolves_aliases_to_canonical_team_names(tmp_path: Path) -> None:
    games = tmp_path / "games.tsv"
    games.write_text(GAMES.replace("Team A", "Alpha"), encoding="utf-8")
    (tmp_path / "teams.toml").write_text(
        TEAMS.replace('name = "Team A"', 'name = "Team A"\naliases = ["Alpha"]'), encoding="utf-8"
    )
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out)])

    rankings = (out / "rankings_output.tsv").read_text(encoding="utf-8")
    assert "\tTeam A\t" in rankings and "Alpha" not in rankings


def test_cli_rejects_games_with_a_team_that_is_not_in_the_roster(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    games = tmp_path / "games.tsv"
    games.write_text(GAMES.replace("Team C", "Team X"), encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        main(["--input", str(games), "--output-dir", str(tmp_path / "out")])

    assert exc.value.code == 1
    assert "Team X" in capsys.readouterr().err


def test_cli_without_games_ranks_every_roster_team_at_the_starting_rating(tmp_path: Path) -> None:
    """Before the first game the rankings page lists every roster team at 0.5 under a start-of-season week."""
    games = tmp_path / "games.tsv"
    games.write_text(GAMES.splitlines()[0] + "\n", encoding="utf-8")
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    out = tmp_path / "out"

    main(["--input", str(games), "--output-dir", str(out)])

    assert "Week 00 - Start of season" in (out / "mhc_rankings_report.html").read_text(encoding="utf-8")
    assert (out / "rankings_output.tsv").read_text(encoding="utf-8").count("\t0.5000\t0.5000\t") == 3


def test_cli_without_games_or_roster_is_an_error(tmp_path: Path) -> None:
    games = tmp_path / "games.tsv"
    games.write_text(GAMES.splitlines()[0] + "\n", encoding="utf-8")

    with pytest.raises(SystemExit):
        main(["--input", str(games), "--output-dir", str(tmp_path / "out")])
