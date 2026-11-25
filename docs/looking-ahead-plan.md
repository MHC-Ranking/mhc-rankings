# Looking Ahead: Implementation Plan

## Goal

Extend the team reports page with remaining regular-season schedule context and a next-game-week projection, without adding columns to the rankings page's already-full main table. Add a separate Look Ahead report page with current standings, schedule metrics, next-week ranges, and the rankings page's weekly charts with shaded outlook ranges.

The first projection model will enumerate regulation wins and losses for games in the next scheduled Monday-Sunday week. It will recompute Colley ratings, SOS, and rankings for each joint outcome combination and summarize the minimum and maximum values per team. These are possible ranges, not probabilities or forecasts.

## Definitions and Boundaries

- **SOSF (Strength of Schedule, Future):** For each team, average the current ratings of its opponents across all remaining scheduled regular-season games. Count each scheduled matchup once.
- **SOSP (Strength of Schedule, Projected):** Average the current ratings of opponents across the team's played and remaining scheduled regular-season games. This is a whole-season schedule measure using ratings as they currently stand; it does not simulate future opponent ratings.
- **Next week:** The next Monday-Sunday week containing scheduled regular-season games, based on the schedule dates.
- **Regulation outcome scenarios:** Each next-week game has two outcomes, a regulation win for either side. No overtime or tie outcomes are included in this initial model.
- **Projected rank:** Rank each scenario using the existing ranking order. Since future scorelines are not simulated, hold each team's current goal differential and goals against fixed as tie-breakers, and disclose this assumption.
- **Future game-log entries:** Keep known date, opponent, and home/away information; display `-` for results, scores, goal differential, and post-game values that are not yet known.
- **Projected chart range:** On the Look Ahead report's weekly charts, shade each team's next-week range from its final actual point. The team report's Rating and Strength of Schedule chart shows actual history only.

## Architecture Considerations

The current dependency flow separates acquisition, computation, and presentation: `app.py` orchestrates; `scraper.py` handles GameSheet data; `rankings_math.py` and the ranking engine compute ratings; `reporting.py` assembles team view data; and `plotting.py` builds charts. Keep these responsibilities intact:

- Add typed scheduled-game data and GameSheet parsing at the scraper boundary. Do not pass raw API dictionaries into ranking calculations or templates.
- Keep network access out of `rankings_math.py`, `reporting.py`, and `plotting.py`. Fetch and canonicalize the schedule in the application orchestration layer, then pass explicit schedule data to pure calculations and renderers.
- Reuse the existing ranking engine and `ranking_key` behavior for every outcome scenario; do not duplicate Colley formulas or tie-breaking logic. Expose a reusable computation boundary if scenario code needs to replay completed and hypothetical games.
- Keep schedule-derived values and projected bounds in explicit team-report data, separate from `TeamRecord`'s current-season actuals. Pass prepared values to reporting and plotting rather than making either layer infer schedule or simulation semantics.
- Keep the feature optional. If no schedule URL is configured, no future games are returned, or schedule retrieval fails, continue generating the existing report without future rows or projection bands. Surface a concise warning for retrieval failures rather than making an external service outage block rankings generation.
- The league typically has about five games per week, so exhaustive enumeration is expected to evaluate about 32 joint scenarios. Enumerate every scenario exactly; do not silently cap or approximate the possible ranges. Keep the scenario count observable and revisit the approach only if actual schedule sizes grow materially.
- Include ranking ranges in this implementation. Since future scorelines are not projected, hold each team's current goal differential and goals against fixed while applying the existing `ranking_key` to each scenario's projected rating.

## Decisions Recorded

- **Schedule failure behavior:** Continue writing the report without future schedule data if schedule retrieval fails.
- **Scenario size:** The league averages about five games per week; enumerate all regulation win/loss combinations exactly (typically 32 scenarios).
- **Feature scope:** Do not defer requested features, including possible ranking ranges.
- **Calculation boundary:** Use a dedicated `looking_ahead.py` module for schedule-derived metrics and projections.
- **Projected-rank tie-breaks:** Use current goal differential and goals against unchanged in each scenario, because future scorelines are not modeled.

## Implementation Checklist

- [x] **Confirm schedule input behavior.** Reuse the roster's `schedule_url`; verify its GameSheet API response includes scheduled games and dates, and handle absent URLs, blocked responses, duplicate entries, and unknown roster teams consistently with the existing scraper.
- [x] **Represent remaining games.** Add a scheduled-game representation separate from the completed-game model, then canonicalize and sort scheduled games by date. Ensure only regular-season games are included where the configured source permits filtering.
- [x] **Calculate SOSF and SOSP.** Use current final ratings as the opponent ratings. Define behavior for teams with no remaining games (SOSF unavailable, rendered as `-`) and no season games (SOSP based on scheduled opponents only; if none, rendered as `-`).
- [x] **Extend team logs.** Merge each team's completed log with its remaining scheduled games in chronological order. Preserve existing actual-game values and set unknown future values to `-` in the rendered table.
- [x] **Implement `looking_ahead.py`.** Keep schedule-derived team metrics and next-week scenario evaluation together behind explicit typed inputs/outputs. Reuse shared ranking behavior from existing modules; do not duplicate Colley calculations or introduce network calls here.
- [x] **Simulate next-week rating, SOS, and rank ranges.** For every joint combination of regulation outcomes, apply next week's games to a fresh ranking engine initialized with all completed games, then collect each team's extrema. Use the confirmed tie-break policy for ranks.
- [x] **Keep the header focused on current standings.** Leave current rank, rating, record, SOS, and GF/GA in the header summary; keep next-week ranges and future SOS metrics in the Looking Ahead bar. Keep the rankings page's main table unchanged.
- [x] **Add the Looking Ahead bar at the report end.** After each team's game log and note, show the next-week rating and rank ranges, SOSF, SOSP, and current SOS in a distinct smaller-text bar. Name the opponent in the title when a next game is scheduled.
- [x] **Update the rating/SOS chart.** Rename it to “Rating and Strength of Schedule,” set the y-axis range to 0.0-1.0, and show actual history only; projected ranges live on the Look Ahead report instead.
- [x] **Add a separate Look Ahead report page.** Start with current rank, team, rating, and SOS followed by the schedule-derived values and next-week ranges. Reuse the weekly rating, rank, and SOS charts with each team's next-week range shaded, and link the page from the rankings report and landing page.
- [x] **Refresh source index.** Update `docs/source-index.md` for any changed functions, signatures, behaviors, and line counts, following `.github/copilot-instructions.md`.

## Likely Code Areas

- `src/mhc_rankings/scraper.py`: scheduled-game parsing and source/API handling.
- `src/mhc_rankings/looking_ahead.py` (new): schedule-derived SOSF/SOSP, next-week scenario enumeration, and rating/SOS/rank ranges.
- `src/mhc_rankings/rankings_math.py`: reusable ranking computation and completed-game-log behavior used by the new module.
- `src/mhc_rankings/app.py`: load schedule data and pass calculations into reporting.
- `src/mhc_rankings/reporting.py`: construct team-report view data.
- `src/mhc_rankings/plotting.py`: actual history, chart title, fixed axis range, and Look Ahead report range bands.
- `src/mhc_rankings/templates/team_reports.html`: summary metrics, tooltips, future game rows, and plot placement.
- `tests/test_scraper.py`, `tests/test_looking_ahead.py` (new), `tests/test_plotting.py`, and `tests/test_reporting.py`: focused parsing, calculation, chart, and rendering coverage.

## Verification Checklist

- [x] Scheduled-game parsing tests cover valid scheduled records, filtering, malformed/missing schedule data, duplicate games, and roster-name canonicalization.
- [x] Calculation tests verify SOSF/SOSP opponent averaging, no-future-game behavior, per-game counting, and rating/SOS/rank extrema over known regulation scenarios.
- [x] Scenario tests verify completed results remain in the base state, same-week games are simulated jointly, and each outcome affects both teams' projected values.
- [x] Rank tests verify ties follow the confirmed policy for current goal-differential/goals-against tie-breaks when future scores are unknown.
- [x] Game-log rendering tests verify future entries are ordered correctly, retain date/opponent/home-away, and use `-` for all unavailable result/post-game fields.
- [x] Team-report tests verify both SOS values and tooltip descriptions are rendered, and missing schedule/projection data does not break report generation.
- [x] Team-report tests verify each team's numerical next-week rating and rank ranges appear in the Looking Ahead bar, not the header.
- [x] Team-report tests verify the Looking Ahead bar includes current SOS, names the next opponent, and has a distinct style after the game log.
- [x] Plot tests verify the team chart's title, fixed 0.0-1.0 axis, and absence of projected bands, and the Look Ahead report's shaded weekly ranges.
- [x] Run focused tests for the touched modules, then the full test suite and lint/type checks required by the repository. The focused feature suite passed; full pytest still has four pre-existing rankings-page assertion failures. No lint/type check is configured; `compileall` passed.
- [x] Generate a report from a representative season dataset and inspect the team report HTML for layout, empty-schedule behavior, and future-game placeholders. The JV season report rendered all 10 sections with the schedule loader stubbed empty; placeholder rows are covered by focused tests.

## UI Direction

Keep the rankings page's main table as-is. On each team report, reserve the header summary for current rank, rating, record, SOS, and GF/GA. Place the next-week rating and rank ranges, SOSF, SOSP, and current SOS in a smaller, distinct bar after the game log; title it “Looking Ahead - After the next game against <opponent>” when an upcoming opponent is known. Place that title above the bar, not inside it, so the bar stays vertically compact. Give SOSF/SOSP native hover/focus tooltips. Append upcoming games to the existing game log using the same row structure and `-` placeholders. The “Rating and Strength of Schedule” plot shows actual lines only.

The separate Look Ahead report begins with current rank, team, games played, rating, and SOS before its next-week ranges and schedule metrics. It then displays the three weekly charts from the rankings page with per-team projected bands; its range table explains that scenarios are possibilities, not probabilities.