"""Tests for the GameSheet results scraper."""

import json
import urllib.error
from pathlib import Path
from typing import Any

import pytest

from mhc_rankings import scraper
from mhc_rankings.io import load_games_data
from mhc_rankings.scraper import (
    ScrapeBlockedError,
    fetch_game_dicts,
    load_games,
    main,
    parse_games,
    season_id_from_url,
    write_tsv,
)


def _game(game_id: int, number: str, date: str, away: tuple[str, int], home: tuple[str, int], **extra: Any) -> dict[str, Any]:
    """Build a game object shaped like GameSheet's embedded data."""
    return {
        "gameId": game_id,
        "number": number,
        "date": date,
        "status": extra.pop("status", "final"),
        "location": "Rockville 1",
        "visitor": {"title": away[0], "goals": away[1], "goalsByPeriod": extra.pop("periods", {"1": 0, "final": away[1]})},
        "home": {"title": home[0], "goals": home[1], "goalsByPeriod": {"final": home[1]}},
    }


def _page(*pages: list[dict[str, Any]]) -> str:
    """Wrap pages of games in HTML the way Next.js embeds its flight data."""
    payload = json.dumps({"pages": [{"games": p, "meta": {}} for p in pages]}, separators=(",", ":"))
    chunk = json.dumps(payload)[1:-1]
    return f'<html><script>self.__next_f.push([1,"{chunk}"])</script></html>'


PAGE = _page(
    [
        _game(2, "MHC - JV - 2", "Oct 2, 2026", ("Walter Johnson JV", 4), ("Silver Spring JV", 3), periods={"1": 1, "OT": 1, "final": 4}),
        _game(1, "MHC - JV - 1", "Sep 25, 2026", ("DC Stars JV", 6), ("Sherwood JV", 0)),
    ],
    [
        _game(1, "MHC - JV - 1", "Sep 25, 2026", ("DC Stars JV", 6), ("Sherwood JV", 0)),
        _game(3, "MHC - JV - 3", "Oct 9, 2026", ("A JV", 0), ("B JV", 0), status="scheduled"),
    ],
)


def test_parse_games_filters_dedupes_and_sorts() -> None:
    """Only final games are kept, once each, oldest first, with overtime flagged."""
    games = parse_games(PAGE)
    assert [g.as_row() for g in games] == [
        ["Sep 25, 2026", "DC Stars JV", "6-0", "Sherwood JV", "Rockville 1", "MHC - JV - 1", "", ""],
        ["Oct 2, 2026", "Walter Johnson JV", "4-3", "Silver Spring JV", "Rockville 1", "MHC - JV - 2", "OT", ""],
    ]


def test_parse_games_adds_game_urls_from_season_id() -> None:
    """With a season id each game links to its GameSheet page by gameId."""
    games = parse_games(PAGE, season_id="15412")
    assert [g.game_url for g in games] == [
        "https://gamesheetstats.com/seasons/15412/games/1",
        "https://gamesheetstats.com/seasons/15412/games/2",
    ]


def test_season_id_is_read_from_source_url() -> None:
    """The season id comes from a /seasons/<id>/ URL; other sources give none."""
    assert season_id_from_url("https://gamesheetstats.com/seasons/15412/games?x=1") == "15412"
    assert season_id_from_url("/tmp/saved-page.html") == ""


def test_main_writes_game_url_column(tmp_path: Path) -> None:
    """`--season-id` fills the Game URL column of the written TSV."""
    page = tmp_path / "page.html"
    page.write_text(PAGE, encoding="utf-8")
    out = tmp_path / "o.tsv"
    assert main([str(page), str(out), "--season-id", "15412"]) == 0
    rows = out.read_text(encoding="utf-8").splitlines()
    assert rows[0].split("\t")[-1] == "Game URL"
    assert rows[1].split("\t")[-1] == "https://gamesheetstats.com/seasons/15412/games/1"


def test_tied_games_are_marked_overtime() -> None:
    """A game with equal scores is marked OT, extra periods are OT, and a decided game stays blank."""
    page = _page(
        [
            _game(1, "G1", "Oct 2, 2026", ("A", 2), ("B", 2)),
            _game(2, "G2", "Oct 3, 2026", ("C", 1), ("D", 1), periods={"1": 0, "OT": 0, "final": 1}),
            _game(3, "G3", "Oct 4, 2026", ("E", 3), ("F", 1)),
            _game(4, "G4", "Oct 5, 2026", ("G", 0), ("H", 0)),
        ]
    )
    assert [g.overtime for g in parse_games(page)] == ["OT", "OT", "", "OT"]


def test_parse_games_detects_bot_challenge() -> None:
    """A Cloudflare challenge page raises a clear error."""
    with pytest.raises(ScrapeBlockedError):
        parse_games("<html><title>Just a moment...</title></html>")


def test_parse_games_requires_embedded_data() -> None:
    """Pages without embedded games are rejected."""
    with pytest.raises(ValueError):
        parse_games("<html>No games found.</html>")


def test_output_round_trips_through_loader(tmp_path: Path) -> None:
    """The TSV written is readable by the ratings loader."""
    out = tmp_path / "out" / "games.tsv"
    write_tsv(parse_games(PAGE), out)
    df = load_games_data(out)
    assert list(df["Home Score"]) == [0, 3]


def test_main_reports_blocked_page(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The CLI exits non-zero when given a challenge page."""
    page = tmp_path / "page.html"
    page.write_text("<title>Just a moment...</title>", encoding="utf-8")
    assert main([str(page), str(tmp_path / "o.tsv")]) == 1
    assert "bot challenge" in capsys.readouterr().err


URL = (
    "https://gamesheetstats.com/seasons/10312/games?configuration[compact-view]=true"
    "&filter[division]=83124,57193&filter[type]=regular_season&filter[status]=completed"
)


def _api(monkeypatch: pytest.MonkeyPatch, games: list[dict[str, Any]], page_size: int) -> list[str]:
    """Serve `games` from a fake paged endpoint and return the URLs requested."""
    requested: list[str] = []

    def fake_get_json(url: str) -> dict[str, Any]:
        requested.append(url)
        offset = int(url.split("offset=")[1].split("&")[0])
        return {"data": games[offset : offset + page_size], "meta": {"total": len(games), "filtered": len(games)}}

    monkeypatch.setattr(scraper, "_get_json", fake_get_json)
    return requested


def test_url_source_reads_every_page_of_games(monkeypatch: pytest.MonkeyPatch) -> None:
    """A URL source is read through the paged endpoint with the page's season, division and type filters."""
    games = [_game(n, f"G{n}", "Oct 2, 2026", ("A", n), ("B", 0)) for n in range(1, 6)]
    requested = _api(monkeypatch, games, page_size=2)

    assert [g["gameId"] for g in fetch_game_dicts(URL)] == [1, 2, 3, 4, 5]
    assert len(requested) == 3
    assert requested[0].startswith("https://gamesheetstats.com/api/unified-games/10312?")
    assert "division=83124%2C57193" in requested[0]
    assert "gameType=regular_season" in requested[0]


def test_load_games_from_url_keeps_final_games_with_links(monkeypatch: pytest.MonkeyPatch) -> None:
    """Only final games are kept, oldest first, each linked to its game page."""
    games = [
        _game(2, "G2", "Oct 9, 2026", ("C", 1), ("D", 0)),
        _game(1, "G1", "Oct 2, 2026", ("A", 2), ("B", 1)),
        _game(3, "G3", "Oct 16, 2026", ("E", 0), ("F", 0), status="scheduled"),
    ]
    _api(monkeypatch, games, page_size=100)
    loaded = load_games(URL, "10312")
    assert [g.game_id for g in loaded] == ["G1", "G2"]
    assert loaded[0].game_url == "https://gamesheetstats.com/seasons/10312/games/1"


def test_load_games_from_url_without_completed_games_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """A season with no completed games is reported rather than written as an empty file."""
    _api(monkeypatch, [_game(1, "G1", "Oct 2, 2026", ("A", 0), ("B", 0), status="scheduled")], page_size=100)
    with pytest.raises(ValueError):
        load_games(URL)


def test_refused_request_is_reported_as_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 403 from the site raises the blocked error instead of a traceback."""

    def refuse(request: Any, timeout: int) -> Any:
        raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {}, None)  # type: ignore[arg-type]

    monkeypatch.setattr(scraper.urllib.request, "urlopen", refuse)
    with pytest.raises(ScrapeBlockedError):
        scraper._get_json("https://gamesheetstats.com/api/unified-games/1")
