# MHC Rankings

MHC Rankings is a Python-based tool for calculating mathematically robust team rankings using advanced ranking algorithms. Originally designed for analyzing hockey game results, it uses the **Colley Matrix** method. It generates accurate ratings, tracks week-by-week progress, calculates Strength of Schedule (SOS), and produces beautiful, interactive HTML reports.

## Features

- **Colley Matrix Ranking:** A bias-free, resume-based ranking system that solves a system of linear equations based on wins, losses, and opponent strength. Margin of victory is deliberately ignored.
- **Strength of Schedule (SOS):** Automatically tracks and computes the SOS for every team using engine-specific logic.
- **Weekly Progress Tracking:** Computes how team rankings, ratings, and SOS change on a week-by-week basis.
- **Interactive HTML Reports:** Generates responsive HTML reports with interactive progress plots (defaulting to Plotly, but supporting Matplotlib), including a dedicated "Rankings Progress" chart.
- **Data Export:** Outputs raw ranking data and the complete state matrix into easy-to-read TSV files.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (for dependency management and running the app)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/brakedust/mhc-rankings.git
   cd mhc-rankings
   ```

2. Sync dependencies:
   ```bash
   uv sync
   ```

## Usage

You can run the ranking generator using `uv run`. 

```bash
uv run mhc-rankings --input mhc-results/jv2026-27/jv-game-results_2026-27.tsv --output-dir mhc-results/jv2026-27/rankings
```

The command reads `teams.toml` from the same folder as the games file (team short names, GameSheet links, colors). To rebuild every division that has a games file, run `./generate_all.sh`.

### Weekly Update

Each division's `teams.toml` has a top-level `games_url` (the GameSheet completed-games page). To refresh a division in one step:

```bash
uv run mhc-weekly mhc-results/jv2026-27/jv-game-results_2026-27.tsv --title "MHC JV Rankings"
```

This scrapes the results, rewrites the games file, builds the rankings and team reports in a `rankings` folder beside it, and writes an `index.html` linking them. If GameSheet blocks the request, a team is unknown, or the site returns fewer games than the file already holds, the command stops with an explanation and changes nothing. Use `--source` to point at a different URL or a saved HTML page, and `--output-dir` to choose where the reports go.

### Command Line Arguments

- `--input` (Required): Path to the games TSV file.
- `--output-dir`: Directory to save the generated report and data files. Defaults to the current directory (`.`).
- `--skip-raw`: Skip saving the raw TSV data files to the output directory.

### Input Data Format

The input should be a TSV (Tab-Separated Values) file containing the following columns at a minimum:
- `Date` (e.g., `2025-11-20`)
- `Away Team`
- `Home Team`
- `Score` (Formatted as `AwayScore-HomeScore`, e.g., `3-2`)

Optional: `Overtime` (`OT`, also used for ties) and `Game URL` (a link to the game's GameSheet page, which turns the Last Game result into a link). The scraper fills `Game URL` when the source is a GameSheet URL or `--season-id` is given. In `teams.toml`, an optional top-level `schedule_url` adds a schedule link under the rankings table.

### Outputs

When run, the application will generate the following in the specified output directory:
- `mhc_rankings_report.html`: The main interactive visual report containing the table and progress plots.
- `rankings_output.tsv`: Final rankings table data.
- `weekly_ratings_output.tsv`: Matrix of team ratings over time.
- `colley_matrix_output.tsv`: The final calculated Colley Matrix.

## 2025-26 Data Processing

The game results from 2025-26 are in `mhc-results/varsity2025-26`. Rankings are generated with the Colley method:

```bash
uv run mhc-rankings --input mhc-results/varsity2025-26/v-game-results_2025-26.tsv --output-dir mhc-results/varsity2025-26/rankings
```

## References

- Colley, Wesley N. (Ph.D., Princeton University). *[Colley’s Bias Free College Football Ranking Method: The Colley Matrix Explained](https://www.colleyrankings.com/matrate.pdf)*

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.