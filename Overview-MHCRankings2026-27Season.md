# Overview - MHC Rankings 2026-27 Season

We are getting ready to start the 2026-2027 season.  We have settled on the using the colley method.  This repo is a fork of the orignal repo, so we can tear out the stuff we don't want.  Develop a phased plan with a checklist that will implement the items below.

Discrete Actions
* Remove BT-ELO and variants from code
* Remove BT-ELO and variants from documentation

* Plots should be 15% smaller in height
* Plots should be in a tab control sort of thing
* If a url is given for a game in the input file, that url should be linked if that 
  game shows up in the "Last Game" column
* We will want documentation at the bottom to be given more in layman's terms.  What is the colley ranking method at it's core.  We can leave the description on the main rankings page as is, but add the simpler explanation first.
* In the rankings table the team name should be linked to their Gamesheets page

Add a link for game schedule: https://gamesheetstats.com/seasons/15412/games?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled


# Varsity Teams:

## Winston Churchill
Abbreviation: Church
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531414/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: Blue, Grey

## Silver Spring
Abbreviation: SS
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531416/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: Red, Black

## Upper Montgomery
Abbreviation: UML
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531417/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: Yellow, Green

## Richard Montgomery
Abbreviation: RM
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531420/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: Yellow, Black

## Central MOCO
Abbreviation: CenMOCO
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531422/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: White, Royal Blue

## DC Stars
Abbreviation: DC
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531418/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: Red, White

## Bethesda-Chevy Chase
Abbreviation: BCC
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531411/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: Navy Blue, Yellow

## Walt Whitman
Abbreviation: Whit
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531412/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Color: #02a7e2

## Sherwood
Abbreviation: Sher
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531421/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: Navy Blue, White

## Walter Johnson
Abbreviation: WJ
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531413/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: Black, White

## Rockville-Magruder
Abbreviation: RAM
Gamesheets Page: https://gamesheetstats.com/seasons/15412/teams/531419/preview?configuration%5Bcompact-view%5D=true&configuration%5Bprimary-colour%5D=C80F2E&configuration%5Bsecondary-colour%5D=041E42&filter%5Bdivision%5D=83124&filter%5Btype%5D=regular_season&filter%5Bstatus%5D=scheduled
Colors: Red, Yellow, Black


---

# Implementation Plan

Decisions from the planning interview:
* Collapse to Colley only in practice, but keep the pluggable `engines/` layer (Colley is the only engine).
* Remove the method-comparison page and `method_compare.py`.
* Drop `--method`, `--use-movm`, `--max-gd` and per-method output folders; one output folder.
* Keep all existing 2025-26 data and scratch files in place (no deletions or archiving).
* Input TSV gets a `Game URL` column, filled by the scraper; the Last Game result text becomes the link.
* Plots: Plotly only, all current plots as tabs on the rankings page only, 15% less height.
* Docs: plain-language Colley section first, existing technical text kept in a collapsed "Technical details" section.
* Team data moves to a `teams.toml` in each division's 2026-27 folder (varsity and jv); each division captures its own team names.
* Varsity has 11 teams; JV has 10 because Richard Montgomery and Sherwood field one combined JV team (abbreviation RMS, Richard Montgomery colors: Yellow, Black).
* JV team names are the varsity name plus " JV" (e.g. "Walter Johnson JV"); the exception is the combined team, named "Richard Montgomery-Sherwood JV" as on GameSheet.
* Team colors: color chips by team names in the table, team colors in plots.
* Schedule link goes below the rankings table.
* Weekly update is one command: scrape, rank, write index page.

Open items:
- [x] Choose plain-language doc length: option (a), about 3 short paragraphs plus a tiny worked example, with a table of the share of a point for each outcome.
- [x] Supply JV GameSheet team URLs (division 83134); JV team IDs can be read from the JV games page data.
- [ ] Decide what to do with `generate_all.sh` (it uses the removed `--method` options): replace with the weekly command, or leave stale since old data is kept.
- [ ] Decide whether the existing BT-ELO output folders under `data/` stay as-is (kept, not regenerated).
- [ ] Confirm that the current CLI default (no `--method`) means Colley.

## Phase 1: Remove BT-ELO and variants
- [x] Delete `engines/bt_elo.py` and its tests; drop BT-ELO from the engine registry in `engines/__init__.py`.
- [x] Remove MoVM / `max-gd` code paths and related math from `rankings_math.py`.
- [x] Delete `method_compare.py` and `templates/compare.html`.
- [x] Remove BT-ELO text from `docs/algorithms.md`, `docs/ratings_options.md`, README; delete `docs/ranking_methods_comparison.md`.
- [x] Remove BT-ELO sections from report templates and plot code (weekly Elo ratings, etc.).
- [x] `uv run pytest` passes.

## Phase 2: Team configuration
- [x] Create `teams.toml` next to each games file: `mhc-results/varsity2026-27/teams.toml` (games in `v-game-results_2026-27.tsv`) and `mhc-results/jv2026-27/teams.toml` (games in `jv-game-results_2026-27.tsv`): name, abbreviation, GameSheet team URL, colors.
- [x] Varsity file has 11 teams; JV file has 10, with a combined Richard Montgomery-Sherwood JV team (RMS, yellow and black).
- [x] Load the file in the input folder from a typed `teams.py` (dataclass), replacing the `abbrev_to_team` dicts.
- [x] Remove Wootton and NWQO; add Central MOCO (CenMOCO, 531422).
- [x] Map GameSheet names to canonical names per division: varsity names as listed above (e.g. "DC Stars"); JV names are the varsity name plus " JV" (e.g. "Walter Johnson JV"), except "Richard Montgomery-Sherwood JV".
- [x] Tests: every team has URL and at least one color; unknown names raise a clear error; team counts are 11 and 10.

## Phase 3: Colley-only CLI and outputs
- [x] Simplify `app.py` arguments; single `--output-dir`; take the games TSV path (`mhc-results/varsity2026-27/v-game-results_2026-27.tsv` or `mhc-results/jv2026-27/jv-game-results_2026-27.tsv`) and load `teams.toml` from the same folder.
- [x] Update `README.md` usage; update or replace `generate_all.sh`.
- [x] Tests for the CLI end to end on a small TSV.

## Phase 4: Game URL column and links
- [x] Scraper writes `Game URL` (from the GameSheet gameId) and tests cover it.
- [x] Loader (`io.py`) accepts the optional column; `stats.py` carries the URL into `last_game`.
- [x] Last Game cell links its result text when a URL exists; escape text and URL.
- [x] Team names in the rankings table link to the team GameSheet page.
- [x] Schedule link below the rankings table.
- [x] Color chips beside team names.
- [x] Tests for linking and escaping.

## Phase 5: Plots
- [x] Remove matplotlib plotting; use Plotly only.
- [x] Reduce plot heights by 15%.
- [x] Put all plots in an accessible tab control (keyboard navigable); resize Plotly on tab switch.
- [x] Use team colors in plot traces.
- [x] Visual check in the browser (headless Firefox screenshots; tab clicks and arrow keys still to be tried by hand).

## Phase 6: Documentation for parents and players
- [x] Draft both layman options (3 paragraphs plus example; one paragraph) for you to choose.
- [x] Put the chosen text first on the docs section; wrap existing text in a collapsed "Technical details".
- [x] Update `mkdoc.py`/`doc.html` and tests if needed.

## Phase 7: Weekly workflow
- [ ] One command: scrape, rank, write the index page; refuse to publish on scrape failure.
- [ ] Update `weekly-update.prompt.md` to call it (varsity and `jv` test option).
- [ ] Add a test using a saved page fixture.
