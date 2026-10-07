#!/bin/bash
set -e

echo "Generating Colley..."
uv run mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey/colley --method colley

echo "Generating BT-Elo..."
uv run mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey/bt-elo --method bt-elo

echo "Generating BT-Elo with MoVM..."
uv run mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey/bt-elo-movm --method bt-elo --use-movm --max-gd 5

echo "Generating BT-Elo with MoVM (Reversed)..."
uv run mhc-rankings --input data/mhc-hockey/game_results_2025-26-reversed.tsv --output-dir data/mhc-hockey/bt-elo-movm-rev --method bt-elo --use-movm --max-gd 5

echo "Generating Comparison Table..."
uv run python src/mhc_rankings/method_compare.py

echo "Done!"
