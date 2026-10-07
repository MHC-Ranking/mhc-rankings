"""End-to-end test of the rankings command line."""

from pathlib import Path

import pytest

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
    assert "https://example.com/team" in report
