"""Tests for rosters loaded from each division's teams.toml."""

from pathlib import Path

import pandas as pd
import pytest

from mhc_rankings.scraper import Game, canonicalize
from mhc_rankings.teams import Roster, Team, UnknownTeamError, load_roster

RESULTS = Path(__file__).parent.parent / "mhc-results"
VARSITY = RESULTS / "varsity2026-27" / "teams.toml"
VARSITY_2025 = RESULTS / "varsity2025-26" / "teams.toml"
JV = RESULTS / "jv2026-27" / "teams.toml"


def _write(tmp_path: Path, body: str) -> Path:
    """Write `body` to a teams.toml in `tmp_path` and return its path."""
    path = tmp_path / "teams.toml"
    path.write_text(body, encoding="utf-8")
    return path


@pytest.mark.parametrize(("path", "count"), [(VARSITY, 11), (JV, 10)])
def test_division_rosters_are_complete(path: Path, count: int) -> None:
    """Each division has the expected team count; every team has a GameSheet URL and a color."""
    roster = load_roster(path)
    assert len(roster) == count
    for team in roster.teams:
        assert team.url.startswith("https://gamesheetstats.com/")
        assert team.colors, team.name
        assert team.abbreviation, team.name


def test_jv_names_follow_varsity_names() -> None:
    """JV names are the varsity name plus ' JV', except the combined Richard Montgomery-Sherwood team."""
    varsity = {t.name for t in load_roster(VARSITY).teams}
    jv = {t.name for t in load_roster(JV).teams}
    assert jv - {f"{n} JV" for n in varsity} == {"Richard Montgomery-Sherwood JV"}
    assert load_roster(JV).resolve("Richard Montgomery-Sherwood JV").abbreviation == "RMS"


def test_gamesheet_alias_resolves_to_canonical_name() -> None:
    """GameSheet's 'DC Stars Varsity' maps to the canonical 'DC Stars'."""
    assert load_roster(VARSITY).resolve("DC Stars Varsity").name == "DC Stars"


def test_unknown_team_error_lists_known_teams() -> None:
    """An unknown name raises a clear error that names the known teams."""
    with pytest.raises(UnknownTeamError, match="Known teams: .*Sherwood"):
        load_roster(VARSITY).resolve("Wootton")


def test_removed_teams_are_not_in_varsity_roster() -> None:
    """Wootton and NWQO are gone; Central MOCO is present."""
    names = {t.name for t in load_roster(VARSITY).teams}
    assert not names & {"Wootton", "NWQO"}
    assert "Central MOCO" in names


def test_colors_resolve_to_hex(tmp_path: Path) -> None:
    """Named colors and hex values both load as lowercase #rrggbb."""
    path = _write(
        tmp_path,
        '[[team]]\nname = "A"\nabbreviation = "A"\nurl = "u"\ncolors = ["Navy Blue", "#02A7E2"]\n',
    )
    assert load_roster(path).resolve("A").colors == ("#001f5b", "#02a7e2")


def test_unknown_color_is_rejected(tmp_path: Path) -> None:
    """A color that is neither a known name nor hex raises a clear error."""
    path = _write(tmp_path, '[[team]]\nname = "A"\nabbreviation = "A"\nurl = "u"\ncolors = ["Chartreuse"]\n')
    with pytest.raises(ValueError, match="unknown color 'Chartreuse'"):
        load_roster(path)


@pytest.mark.parametrize("missing", ["abbreviation", "colors"])
def test_team_missing_a_field_is_rejected(tmp_path: Path, missing: str) -> None:
    """A team without an abbreviation or color is rejected."""
    fields = {"abbreviation": '"A"', "url": '"u"', "colors": '["Red"]'}
    body = '[[team]]\nname = "A"\n' + "".join(f"{k} = {v}\n" for k, v in fields.items() if k != missing)
    with pytest.raises(ValueError, match=f"missing: {missing}"):
        load_roster(_write(tmp_path, body))


def test_duplicate_names_are_rejected() -> None:
    """Two teams cannot share a name or alias."""
    team = Team("A", "A", "u", ("#000000",))
    with pytest.raises(ValueError, match="Duplicate"):
        Roster([team, Team("B", "B", "u", ("#000000",), aliases=("A",))])


def test_abbreviations_map_names_to_short_names() -> None:
    """The roster maps names, and aliases such as GameSheet's, to abbreviations for the Last Game column."""
    abbreviations = load_roster(VARSITY).abbreviations
    assert abbreviations["Walter Johnson"] == "WJ"
    assert abbreviations["DC Stars Varsity"] == "DC"


def test_varsity_2025_26_roster_covers_its_games_and_links_to_its_season() -> None:
    """The 2025-26 roster differs from 2026-27 (Wootton and NWQO, no Central MOCO), any team URL points at season 10312, and every team in its games is known."""
    old = load_roster(VARSITY_2025)
    names = {t.name for t in old.teams}
    assert {"Wootton", "NWQO"} <= names
    assert "Central MOCO" not in names
    assert all(t.url.startswith("https://gamesheetstats.com/seasons/10312/teams/") for t in old.teams if t.url)
    games = pd.read_csv(VARSITY_2025.parent / "v-game-results_2025-26.tsv", sep="\t")
    for team in set(games["Away Team"]) | set(games["Home Team"]):
        old.resolve(team)


@pytest.mark.parametrize("path", [VARSITY, VARSITY_2025, JV])
def test_team_line_colors_are_distinct(path: Path) -> None:
    """Each team's first color (its plot line) is unique within a division."""
    firsts = [t.colors[0] for t in load_roster(path).teams]
    assert len(firsts) == len(set(firsts))


def test_team_url_is_optional(tmp_path: Path) -> None:
    """A team may omit its URL; it loads with a blank one."""
    path = _write(tmp_path, '[[team]]\nname = "A"\nabbreviation = "A"\ncolors = ["Red"]\n')
    assert load_roster(path).resolve("A").url == ""


def test_canonicalize_renames_games_and_rejects_unknown_teams() -> None:
    """Scraped games use canonical names; a team missing from the roster raises."""
    roster = load_roster(VARSITY)
    game = Game("Oct 1, 2026", "DC Stars Varsity", 2, 1, "Sherwood", "Rink", "1", "")
    renamed = canonicalize([game], roster)[0]
    assert (renamed.away, renamed.home) == ("DC Stars", "Sherwood")
    with pytest.raises(UnknownTeamError):
        canonicalize([Game("Oct 1, 2026", "Wootton", 2, 1, "Sherwood", "Rink", "1", "")], roster)
