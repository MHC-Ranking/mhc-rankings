# Source Index: `src/mhc_rankings`

Map of the package so the structure is clear without reading every file. Line numbers are the line where each
definition starts (for decorated items, the `def`/`class` line) and drift as files change. Refresh them with the
command at the bottom. Maintenance rules are in [.github/copilot-instructions.md](../.github/copilot-instructions.md).

- Package: `mhc_rankings` (src layout, Python >= 3.14, built with `uv_build`).
- Dependencies: jinja2, markdown-it-py, mdit-py-plugins, numpy, pandas, plotly. Tests use pytest.
- Purpose: scrape MHC hockey results from GameSheet, rank teams with the Colley matrix method, and write HTML/TSV reports.

## Entry points (`pyproject.toml` `[project.scripts]`)

| Command | Target | Purpose |
| --- | --- | --- |
| `mhc-rankings` | `mhc_rankings:main` -> `app.main` | Rank a games TSV and write reports |
| `mhc-weekly` | `mhc_rankings.weekly:main` | Scrape, validate, back up, rank, write index page |
| `mkdoc` | `mhc_rankings.mkdoc:main` | Convert a Markdown file to a styled HTML page with TOC |
| (module) | `python -m mhc_rankings.scraper SOURCE OUTPUT` | Scrape only, write a games TSV |

## Data flow

```
GameSheet URL / saved HTML
   -> scraper.load_games -> scraper.canonicalize (uses teams.Roster) -> weekly.check_games -> scraper.write_tsv
games TSV (+ teams.toml beside it)
   -> io.load_games_data -> DataFrame
   -> rankings_math.compute_final_rankings   (engines.ColleyEngine + stats.StatsTracker -> list[TeamRecord])
   -> rankings_math.compute_weekly_ratings   (same, snapshot per game week -> dict[week label, list[TeamRecord]])
   -> rankings_math.compute_team_game_logs   (per-team game-by-game rating/rank)
   -> io.save_*_tsv                          (rankings, weekly ratings, Colley matrix)
   -> reporting.generate_html_report         (plotting.get_plotly_html + templates/report.html)
   -> reporting.generate_team_reports        (plotting.get_team_*_plot_html + templates/team_reports.html)
   -> console.print_rankings_table
   -> weekly.write_index_page                (templates/index.html)  [weekly only]
```

Module dependency summary (arrow = imports): `app` -> `io`, `console`, `rankings_math`, `reporting`, `teams`;
`weekly` -> `app`, `io`, `scraper`, `teams`; `reporting` -> `plotting`, `rankings_math`, `models`, `teams`;
`rankings_math` -> `stats`, `engines`, `models`; `stats`/`io`/`console`/`plotting` -> `models`;
`scraper` -> `teams`; `mkdoc` is standalone.

Conventions worth knowing:

- Games DataFrame columns: `Date`, `Away Team`, `Score` ("a-h"), `Home Team`, `Location`, `Game ID`, `Overtime`, `Game URL`;
  `io.load_games_data` adds `Away Score` and `Home Score`.
- A tied game is always treated as overtime for rating purposes (`rankings_math`).
- Rank order is `stats.ranking_key`: rating, then goal differential, then goals against, then name. Ranks are always
  distinct. The tie-break is deliberately not mentioned on any web page.
- When `teams.toml` exists, every roster team is ranked even with no games (rating 0.5, SOS 0.5); game team names are
  resolved to canonical roster names and an unknown name is an error.
- Weeks run Monday-Sunday and are labelled `"Week 01"`...; `"Week 00"` (`WEEK_ZERO`) is the 0.5 starting point.
- `teams.toml` (beside the games TSV) lists `[[team]]` entries (`name`, `abbreviation`, `colors`, optional `url`, `aliases`)
  and top-level `division`, `schedule_url`, `games_url`. It is optional for `app.main`, required for `weekly.main`.
- `TeamRecord.rank_change` = previous rank - current rank (positive = moved up).

## `__init__.py` (3 lines)

Re-exports `main` from `app` (`__all__ = ["main"]`).

## `app.py` (137 lines) - ranking CLI

| Line | Item | Description |
| --- | --- | --- |
| 23 | `main(argv=None) -> None` | CLI `--input` (games TSV, required), `--output-dir` (default `.`), `--skip-raw`. Loads data and roster; with a roster, maps game team names (aliases) to canonical names, exits 1 on a team not in the roster, and ranks every roster team even with no games. Computes final and weekly rankings, sets `rank_change` from the previous game week, writes raw TSVs (unless `--skip-raw`), `mhc_rankings_report.html`, `mhc_team_reports.html`, and prints the table. Exits 1 on missing input, or an empty games file when there is no roster. |

## `weekly.py` (131 lines) - one-command weekly update

| Line | Item | Description |
| --- | --- | --- |
| 23 | `TEMPLATE_DIR` | Path to `templates/`. |
| 24 | `BACKUP_PREFIX` | `"~backup-"`, prefix for the games-file backup. |
| 27 | `load_recorded_games(games_file)` | Existing games keyed by Game ID; `{}` if the file is missing. |
| 35 | `check_games(games, games_file)` | Validates a scrape (no duplicate IDs, no negative scores or self-play, nothing recorded is missing or changed). Returns count of new games; raises `ValueError`. |
| 73 | `back_up_games_file(games_file)` | Copies the file to `~backup-<name>`; returns path or `None`. |
| 85 | `write_index_page(output_dir, title, latest_date, game_count)` | Renders `templates/index.html` to `index.html`; returns path. |
| 94 | `main(argv=None) -> int` | CLI `games` TSV, `--source`, `--output-dir`, `--title`. Reads `teams.toml` beside the TSV, scrapes, canonicalizes, checks, backs up, writes TSV, calls `app.main`, writes index. Returns 0, or 1 (nothing changed) on error. |

## `scraper.py` (227 lines) - GameSheet scraping

| Line | Item | Description |
| --- | --- | --- |
| 25-36 | Constants | `TSV_HEADER`, `DATE_FORMAT`, `GAME_URL`, `API_URL`, `API_PAGE_SIZE`, `USER_AGENT`, regexes (`_SEASON_RE`, `_PUSH_RE`, `_GAMES_RE`), `_REGULATION_PERIODS`, `_BLOCK_MARKERS`, `_BLOCKED_MESSAGE`. |
| 39 | `class ScrapeBlockedError(RuntimeError)` | Site served a bot challenge instead of results. |
| 44 | `class Game` (frozen dataclass) | One completed game: `date`, `away`, `away_score`, `home_score`, `home`, `location`, `game_id`, `overtime`, `game_url`. |
| 57 | `Game.as_row()` | Row of strings matching `TSV_HEADER`. |
| 63 | `_embedded_text(html)` | Joins Next.js flight-data chunks embedded in the page. |
| 68 | `_game_dicts(text)` | Game objects from every `"games":[...]` array in the payload. |
| 78 | `_overtime_marker(team)` | `"OT"` if the team has goals in non-regulation periods. |
| 83 | `_tie_marker(game)` | `"OT"` if final scores are equal. |
| 88 | `season_id_from_url(source)` | Season id from `/seasons/<id>/`, or `""`. |
| 94 | `games_from_dicts(raw, season_id="")` | Final games only, de-duplicated, oldest first, with game URLs. |
| 117 | `parse_games(html, season_id="")` | Games from saved page HTML; raises `ScrapeBlockedError` or `ValueError` (no data). |
| 133 | `_get_json(url)` | HTTP GET JSON; 403/429/503 or non-JSON -> `ScrapeBlockedError`. |
| 151 | `fetch_game_dicts(source)` | Pages through the site JSON API honoring `filter[division]` / `filter[type]` of the URL. |
| 172 | `load_games(source, season_id="")` | URL (all pages) or saved HTML file -> `list[Game]`. |
| 187 | `canonicalize(games, roster)` | Replace team names with canonical roster names; raises `UnknownTeamError`. |
| 196 | `write_tsv(games, output)` | Write games TSV with `TSV_HEADER`. |
| 205 | `main(argv=None) -> int` | CLI `source output [--teams] [--season-id]`. |

## `teams.py` (124 lines) - roster

| Line | Item | Description |
| --- | --- | --- |
| 8 | `COLOR_HEX` | Color-name -> `#rrggbb` map. |
| 22 | `class UnknownTeamError(ValueError)` | Name not in the roster. |
| 27 | `class Team` (frozen dataclass) | `name`, `abbreviation`, `url`, `colors` (hex tuple), `aliases`. |
| 37 | `class Roster` | Teams in a division, lookup by name or alias. Attributes: `teams`, `schedule_url`, `games_url`, `division`. |
| 40 | `Roster.__init__(teams, schedule_url, games_url, division)` | Indexes names and aliases; raises `ValueError` on duplicates. |
| 60 | `Roster.__len__()` | Number of teams. |
| 64 | `Roster.find(name)` | `Team` or `None`. |
| 68 | `Roster.resolve(name)` | `Team` or raises `UnknownTeamError` listing known names. |
| 81 | `Roster.abbreviations` (property) | name/alias -> abbreviation. |
| 86 | `_color_to_hex(color, team)` | Hex or named color -> `#rrggbb`; raises `ValueError`. |
| 96 | `load_roster(path)` | Parse `teams.toml` into a `Roster`; raises `ValueError` for missing name/abbreviation/colors. |

## `models.py` (27 lines)

| Line | Item | Description |
| --- | --- | --- |
| 4 | `class TeamRecord` (dataclass) | `team`, `rating`, `sos`, `wins`, `ot_wins`, `losses`, `ot_losses`, `t`, `gf`, `ga`, `rank`, `rank_change`, `last_game`, `last_game_url`; derived `gp`, `win_pct`, `gd`. |
| 23 | `TeamRecord.__post_init__()` | Computes `gp` (games played), `win_pct` (OTW = 0.667, OTL = 0.333, T = 0.5 of a win) and `gd`. |

## `stats.py` (81 lines)

| Line | Item | Description |
| --- | --- | --- |
| 6 | `ranking_key(rating, gd, ga, team)` | Standings sort key: rating rounded to 4 decimals (high first), then goal differential (high first), then goals against (low first), then name. Used for every ranking order. |
| 11 | `class StatsTracker` | Cumulative W/OTW/L/OTL/T/GF/GA and Last Game text per team. |
| 14 | `StatsTracker.__init__(teams, abbreviations=None)` | Zeroed stats; abbreviations used in Last Game text. |
| 20 | `StatsTracker.add_game(away, home, away_score, home_score, is_overtime=False, game_url="")` | Update both teams; Last Game reads `@ ABB W 3-1` (away) / `vs ABB L 1-3` (home), with ` (OT)` suffix. |
| 60 | `StatsTracker.build_records(ratings, sos)` | Merge stats with engine output into `TeamRecord`s ordered by `ranking_key` (rank not set). |

## `engines/`

### `engines/base.py` (29 lines)

| Line | Item | Description |
| --- | --- | --- |
| 4 | `class RankingEngine(ABC)` | Interface for ranking methods. |
| 8 | `__init__(teams)` | Abstract. |
| 13 | `add_game(away, home, away_score, home_score, is_overtime=False)` | Abstract; process one result. |
| 18 | `solve()` | Abstract; returns `(ratings, sos)` dicts. |
| 27 | `details` (abstract property) | Method-specific data for reports (the Colley matrix). |

### `engines/colley.py` (102 lines)

| Line | Item | Description |
| --- | --- | --- |
| 23 | `class ColleyEngine(RankingEngine)` | Colley matrix: solves `C r = b`; SOS = average opponent rating. |
| 26 | `__init__(teams)` | `C` starts with 2 on the diagonal, `b` all ones. |
| 39 | `add_game(...)` | Increments `C` diagonals, decrements off-diagonals, updates `b`: regulation win/loss = +/-0.5, overtime win/loss = +/-0.167, ties add nothing. |
| 73 | `solve()` | `numpy.linalg.solve`; SOS = (C[i,i]*r[i] - b[i]) / games played (0.5, the starting rating, if none). |
| 101 | `details` (property) | Returns the `C` ndarray. |

`engines/__init__.py` is empty.

## `rankings_math.py` (221 lines) - computations over the games DataFrame

| Line | Item | Description |
| --- | --- | --- |
| 11 | `START_RATING` | 0.5. |
| 14 | `week_label(number)` | `"Week 03"` style label. |
| 19 | `WEEK_ZERO` | `"Week 00"`. |
| 22 | `_week_ends(dates)` | Sunday ending each date's Monday-Sunday week. |
| 28 | `game_week_ends(df)` | Ordered `{week label: Sunday date}` for weeks with a completed game (no gaps, excludes Week 00). |
| 39 | `get_teams(df, extra_teams=())` | Sorted unique team names from the games plus `extra_teams` (roster teams that have not played). |
| 45 | `_game_url(row)` | Optional `Game URL` or `""`. |
| 50 | `get_engine(teams)` | Returns `ColleyEngine`; change here to swap methods. |
| 54 | `compute_final_rankings(df, abbreviations=None, extra_teams=())` | `(records sorted with rank set, engine.details, teams)` over all games; `extra_teams` are ranked at 0.5 if unplayed. |
| 97 | `compute_weekly_ratings(df, abbreviations=None, extra_teams=())` | `({week label: records}, teams)`: Week 00 start plus a snapshot after each game week, with `rank` and `rank_change`. With no completed games, `{}` unless `extra_teams` are given (then Week 00 only). |
| 156 | `compute_team_game_logs(df, extra_teams=())` | `{team: [dict per game]}` (empty list for unplayed `extra_teams`) with `date`, `opponent`, `is_home`, `team_score`, `opp_score`, `gd`, `ot`, `rating_post`, `sos_post`, `rank_post` (ranked with `ranking_key` using goals to date). |

## `reporting.py` (208 lines) - HTML report generation

| Line | Item | Description |
| --- | --- | --- |
| 21 | `TEMPLATE_DIR` | Path to `templates/`. |
| 22 | `TEAM_REPORTS_FILE` | `"mhc_team_reports.html"`. |
| 26 | `safe_http_url(url)` | URL if http(s), else `""`. |
| 31 | `link_html(text, url)` | Escaped text, as a new-tab link when the URL is safe. |
| 40 | `league_name(roster)` | `"MHC <division>"` or `"MHC"`. |
| 45 | `team_anchor(name)` | `"team-<Name-With-Dashes>"` section id. |
| 50 | `team_cell_html(name)` | Link cell to the team's section in the team reports. |
| 55 | `plot_line_colors(teams, roster)` | Team -> first hex color for chart lines. |
| 67 | `_with_html_cells(record)` | Record dict plus `team_html` and `last_game_html`. |
| 75 | `week_option_label(week, week_end)` | `"Week 03 - Oct 25, 2026"`. |
| 80 | `generate_html_report(date_str, details, teams, weekly_records, output_path, df, roster=None)` | Renders `report.html` (week selector table, three charts, Colley matrix, games list); before any game the table shows Week 00 labelled "Start of season". Template vars: `date`, `league`, `details`, `teams`, `matrix_labels`, `plot_data`, `rank_plot_data`, `sos_plot_data`, `all_weeks_data`, `sorted_weeks`, `week_options`, `title_method`, `games_data`, `schedule_url`. |
| 156 | `generate_team_reports(date_str, rankings, team_logs, output_path, roster=None)` | Renders `team_reports.html` with a section per team (record, game log, two charts). Template vars: `date`, `league`, `team_names`, `teams_data`, `title_method`, `plotly_version`. Note: this environment does not enable autoescape. |

## `plotting.py` (233 lines) - Plotly charts (return HTML div strings)

| Line | Item | Description |
| --- | --- | --- |
| 9-13 | Constants | `PLOT_HEIGHT`, `FONT_FAMILY`, `LEGEND_MARGIN_MAX`, `TEAM_CHART_CONFIG`. |
| 15-21 | `_DASHES`, `_MARKERS`, `_FALLBACK_COLORS` | Style cycles so similar-colored teams stay distinct. |
| 29 | `get_plotly_html(weekly_records, teams, title, ylabel, metric="rating", colors=None, include_plotlyjs=True, abbreviations=None)` | Multi-team weekly line chart for `rating`, `rank` (inverted axis) or `sos`; legend ordered by the final week's ranking; dropdown for All / Top 6 / Bottom 6 / single team. Loads plotly.js from CDN only if `include_plotlyjs`. |
| 161 | `get_team_gd_plot_html(team_logs, team_name)` | Per-game goal-differential bar chart (green/red/grey). |
| 195 | `get_team_rating_sos_plot_html(team_logs, team_name)` | Per-game rating and SOS line chart. |

## `io.py` (93 lines) - TSV read/write

| Line | Item | Description |
| --- | --- | --- |
| 9 | `load_games_data(file_path)` | Read games TSV (a header-only file gives an empty frame), parse `Date`, split `Score` into `Away Score`/`Home Score`, sort by date. |
| 41 | `get_latest_game_date(df)` | Latest date as `"Oct 16, 2026"` or `"Unknown Date"`. |
| 58 | `save_rankings_tsv(rankings, output_path)` | Rank table TSV (`rankings_output.tsv`). |
| 69 | `save_colley_matrix_tsv(C, teams, output_path)` | Colley matrix TSV (`colley_matrix_output.tsv`). |
| 81 | `save_weekly_ratings_tsv(weekly_records, teams, output_path)` | Rating per team per week TSV (`weekly_ratings_output.tsv`). |

## `console.py` (23 lines)

| Line | Item | Description |
| --- | --- | --- |
| 4 | `print_rankings_table(rankings)` | Prints the ranking table with colored rank-change arrows. |

## `mkdoc.py` (103 lines) - Markdown to HTML docs

| Line | Item | Description |
| --- | --- | --- |
| 9 | `slugify(text)` | Heading text -> HTML id. |
| 15 | `extract_text_from_tokens(tokens, start_idx)` | Heading text from inline tokens. |
| 25 | `convert_markdown_to_html(input_path, output_path=None)` | markdown-it + dollarmath (converted to MathJax delimiters), builds TOC, renders `templates/doc.html`. |
| 94 | `main()` | CLI `input_md [-o OUTPUT]`. |

## `templates/` (Jinja2)

| File | Lines | Used by | Content |
| --- | --- | --- | --- |
| `report.html` | 899 | `reporting.generate_html_report` | Rankings page: week selector, rankings table, charts, matrix, games, explanation of Colley. |
| `team_reports.html` | 398 | `reporting.generate_team_reports` | One section per team. |
| `index.html` | 85 | `weekly.write_index_page` | Landing page linking the two reports (`title`, `latest_date`, `game_count`). |
| `doc.html` | 298 | `mkdoc.convert_markdown_to_html` | Document page with TOC sidebar and MathJax (`title`, `toc`, `html_content`). |

## Outside `src/`

| Path | Description |
| --- | --- |
| `tests/test_<module>.py` | One pytest file per module (`app`, `engines`, `io`, `mkdoc`, `plotting`, `rankings_math`, `reporting`, `scraper`, `stats`, `teams`, `weekly`); `tests/fixtures/games_page.html` is a saved GameSheet page. |
| `generate_all.sh` | Reruns `mhc-rankings` (via `uv run`) for each division's games TSV. |
| `colley_matrix.py` | Legacy standalone script (uses matplotlib, not a project dependency); not part of the package. |
| `docs/algorithms.md` -> `docs/algorithms.html` | Algorithm write-up, built with `mkdoc`. |
| `mhc-results/<division><season>/` | Games TSV, `teams.toml`, and generated `rankings/` output. |

## Refreshing line numbers

```bash
grep -nE '^\s*(def |class )|^[A-Z_][A-Z0-9_]* *(:|=)' src/mhc_rankings/*.py src/mhc_rankings/engines/*.py
wc -l src/mhc_rankings/*.py src/mhc_rankings/engines/*.py src/mhc_rankings/templates/*
```
