"""Tests for the one-command weekly update."""

from pathlib import Path

import pytest

from mhc_rankings import weekly
from mhc_rankings.scraper import Game, ScrapeBlockedError
from mhc_rankings.weekly import check_games, main

PAGE = Path(__file__).parent / "fixtures" / "games_page.html"


def _teams(names: str) -> str:
    """Return teams.toml text for 'Team <letter>' for each letter in `names`."""
    return "".join(
        f'[[team]]\nname = "Team {n}"\nabbreviation = "T{n}"\nurl = ""\ncolors = ["#abcdef"]\n\n' for n in names
    )


TEAMS = _teams("ABC")


@pytest.fixture
def division(tmp_path: Path) -> Path:
    """A division folder with a teams.toml and the path of its (not yet written) games file."""
    (tmp_path / "teams.toml").write_text(TEAMS, encoding="utf-8")
    return tmp_path / "games.tsv"


def test_weekly_scrapes_ranks_and_writes_index(division: Path) -> None:
    """A saved page gives a games file, both reports and an index page linking them."""
    assert main([str(division), "--source", str(PAGE), "--title", "Test Rankings"]) == 0

    rows = division.read_text(encoding="utf-8").splitlines()
    assert len(rows) == 4  # header plus the three completed games; the scheduled one is skipped
    assert rows[2].split("\t")[6] == "OT"  # the 2-2 tie is marked as overtime
    out = division.parent / "rankings"
    index = (out / "index.html").read_text(encoding="utf-8")
    assert "Test Rankings" in index
    assert "3 completed games through Oct 16, 2026" in index
    assert 'href="mhc_rankings_report.html"' in index and 'href="mhc_team_reports.html"' in index
    assert (out / "mhc_rankings_report.html").exists() and (out / "mhc_team_reports.html").exists()


def test_weekly_uses_games_url_from_teams_toml(division: Path) -> None:
    """Without --source the games_url in teams.toml is what gets scraped."""
    (division.parent / "teams.toml").write_text(f'games_url = "{PAGE}"\n\n{TEAMS}', encoding="utf-8")
    assert main([str(division)]) == 0
    assert len(division.read_text(encoding="utf-8").splitlines()) == 4


def test_blocked_scrape_changes_nothing(division: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """A blocked scrape leaves the games file alone, writes no reports and reports the error."""
    division.write_text("Date\tAway Team\tScore\tHome Team\tLocation\tGame ID\tOvertime\n", encoding="utf-8")
    before = division.read_text(encoding="utf-8")

    def blocked(source: str, season_id: str = "") -> list[object]:
        raise ScrapeBlockedError("bot challenge")

    monkeypatch.setattr(weekly, "load_games", blocked)
    assert main([str(division), "--source", "https://gamesheetstats.com/seasons/1/games"]) == 1

    assert division.read_text(encoding="utf-8") == before
    assert not (division.parent / "rankings").exists()
    assert "Nothing was changed" in capsys.readouterr().err


def test_scrape_that_drops_recorded_games_is_refused(division: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """If the site returns fewer games than the file already holds, nothing is overwritten."""
    division.write_text(
        "Date\tAway Team\tScore\tHome Team\tLocation\tGame ID\tOvertime\n"
        "Oct 1, 2026\tTeam A\t1-0\tTeam B\tRink 1\tMHC - 99\t\n",
        encoding="utf-8",
    )
    before = division.read_text(encoding="utf-8")

    assert main([str(division), "--source", str(PAGE)]) == 1

    assert division.read_text(encoding="utf-8") == before
    assert "MHC - 99" in capsys.readouterr().err


def test_unknown_team_in_scrape_is_refused(division: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A team missing from teams.toml stops the update before anything is written."""
    (division.parent / "teams.toml").write_text(_teams("AB"), encoding="utf-8")
    assert main([str(division), "--source", str(PAGE)]) == 1
    assert not division.exists()
    assert "Unknown team" in capsys.readouterr().err


def test_missing_source_is_an_error(division: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With no --source and no games_url the command explains what is missing."""
    assert main([str(division)]) == 1
    assert "games_url" in capsys.readouterr().err


def test_first_run_has_nothing_to_back_up(division: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """With no games file yet there is no backup, and every scraped game counts as new."""
    assert main([str(division), "--source", str(PAGE)]) == 0

    assert not (division.parent / "~backup-games.tsv").exists()
    assert "(3 new)" in capsys.readouterr().out


def test_rerun_backs_up_previous_file_beside_it(division: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A second run keeps the previous games file as ~backup-<name> and reports no new games."""
    assert main([str(division), "--source", str(PAGE)]) == 0
    first = division.read_text(encoding="utf-8")
    capsys.readouterr()

    assert main([str(division), "--source", str(PAGE)]) == 0

    assert (division.parent / "~backup-games.tsv").read_text(encoding="utf-8") == first
    out = capsys.readouterr().out
    assert "~backup-games.tsv" in out and "(0 new)" in out


def test_changed_recorded_game_is_refused(division: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """If the site now shows a different score for a recorded game, nothing is overwritten."""
    assert main([str(division), "--source", str(PAGE)]) == 0
    edited = division.read_text(encoding="utf-8").replace("\t3-1\t", "\t9-1\t")
    division.write_text(edited, encoding="utf-8")

    assert main([str(division), "--source", str(PAGE)]) == 1

    assert division.read_text(encoding="utf-8") == edited
    assert not (division.parent / "~backup-games.tsv").exists()
    assert "changes 1 game" in capsys.readouterr().err


def _game(game_id: str, away: str = "Team A", home: str = "Team B", away_score: int = 1, home_score: int = 0) -> Game:
    """Build a completed game for validation tests."""
    return Game("Oct 2, 2026", away, away_score, home_score, home, "Rink 1", game_id, "")


def test_check_games_rejects_repeated_ids(tmp_path: Path) -> None:
    """The same Game ID twice in one scrape is an error."""
    with pytest.raises(ValueError, match="repeats game IDs: MHC - 1"):
        check_games([_game("MHC - 1"), _game("MHC - 1")], tmp_path / "games.tsv")


@pytest.mark.parametrize("game", [_game("MHC - 1", away_score=-1), _game("MHC - 1", home="Team A")])
def test_check_games_rejects_negative_scores_and_self_games(tmp_path: Path, game: Game) -> None:
    """A negative score or a team playing itself is an error."""
    with pytest.raises(ValueError, match="invalid scores or teams in: MHC - 1"):
        check_games([game], tmp_path / "games.tsv")


def test_check_games_accepts_shutouts_and_counts_new_games(tmp_path: Path) -> None:
    """Shutouts (0 goals) are valid, and only games not already recorded are counted as new."""
    games_file = tmp_path / "games.tsv"
    games_file.write_text(
        "Date\tAway Team\tScore\tHome Team\tLocation\tGame ID\tOvertime\n"
        "Oct 2, 2026\tTeam A\t1-0\tTeam B\tRink 1\tMHC - 1\t\n",
        encoding="utf-8",
    )
    assert check_games([_game("MHC - 1"), _game("MHC - 2", away_score=0, home_score=7)], games_file) == 1
