# MHC Rankings

MHC Rankings is a Python-based tool for calculating mathematically robust team rankings using advanced ranking algorithms. Originally designed for analyzing hockey game results, it currently supports both the **Colley Matrix** method and a hybrid **Bradley-Terry / Elo** method. It generates accurate ratings, tracks week-by-week progress, calculates Strength of Schedule (SOS), and produces beautiful, interactive HTML reports.

## Features

- **Multiple Ranking Engines:** 
  - **Colley Matrix:** A bias-free, resume-based ranking system that solves a system of linear equations based on wins, losses, and opponent strength.
  - **Bradley-Terry / Elo:** A predictive, power-based system that iterates chronologically. It uses the Bradley-Terry logistic curve to predict win probabilities and updates Elo ratings based on outcomes. Includes an optional **Margin of Victory Multiplier (MoVM)** to appropriately reward blowouts.
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
uv run mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey --method bt-elo --use-movm --max-gd 4 --include-sos-plot
```

### Command Line Arguments

- `--input` (Required): Path to the input TSV file containing game results.
- `--output-dir`: Directory to save the generated report and data files. Defaults to the current directory (`.`).
- `--method`: The ranking methodology to use. Choices are `colley` or `bt-elo`. Defaults to `colley`.
- `--use-movm`: (BT-Elo Only) Use a Margin of Victory Multiplier to scale Elo exchanges based on goal differentials.
- `--max-gd`: (BT-Elo Only) The maximum goal differential cap allowed in the MoVM calculation. Defaults to `4`.
- `--plot-engine`: The plotting engine to use in the HTML report. Choices are `plotly` or `matplotlib`. Defaults to `plotly`.
- `--skip-raw`: Skip saving the raw TSV data files and plot PNGs to the output directory.
- `--include-sos-plot`: Include an interactive progress plot of the Strength of Schedule in the HTML report.

### Input Data Format

The input should be a TSV (Tab-Separated Values) file containing the following columns at a minimum:
- `Date` (e.g., `2025-11-20`)
- `Away Team`
- `Home Team`
- `Score` (Formatted as `AwayScore-HomeScore`, e.g., `3-2`)

### Outputs

When run, the application will generate the following in the specified output directory:
- `mhc_rankings_report.html`: The main interactive visual report containing the table and progress plots.
- `rankings_output.tsv`: Final rankings table data.
- `weekly_ratings_output.tsv`: Matrix of team ratings over time.
- `colley_matrix_output.tsv`: The final calculated Colley Matrix (if the Colley method was used).

## 2025-26 Data Processing

The game results from the 2025-26 are included in the `data/mhc-hockey` folder.  They have been 
processed using three different schemes.

### Colley Method

```bash
mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey/colley --plot-engine plotly --include-sos-plot --method colley
```

### Bradley-Terry/ELO Hybrid Method 

```bash
mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey/bt-elo --method bt-elo --include-sos-plot --plot-engine plotly
```

### Bradley-Terry/ELO Hybrid Method + Margin of Victory Multiplier

```bash
mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey/bt-elo-movm --method bt-elo --use-movm --max-gd 4 --include-sos-plot --plot-engine plotly
```


## References

- Colley, Wesley N. (Ph.D., Princeton University). *[Colley’s Bias Free College Football Ranking Method: The Colley Matrix Explained](https://www.colleyrankings.com/matrate.pdf)*

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.