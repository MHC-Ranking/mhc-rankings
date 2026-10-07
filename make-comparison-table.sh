#!/bin/bash
uv run mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey/colley --method colley

uv run mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey/colley --method colley

uv run mhc-rankings --input data/mhc-hockey/game_results_2025-26.tsv --output-dir data/mhc-hockey/bt-elo-movm --method bt-elo --use-movm --max-gd 5 

uv run mhc-rankings --input data/mhc-hockey/game_results_2025-26-reversed.tsv --output-dir data/mhc-hockey/bt-elo-movm-rev --method bt-elo --use-movm --max-gd 5 

uv run python src/mhc_rankings/method_compare.py


cp docs/algorithms.html ../brakedust.github.io/
cp data/mhc-hockey/index.html ../brakedust.github.io/
cp data/mhc-hockey/ranking_methods_comparison.html ../brakedust.github.io/

cp -r data/mhc-hockey/colley ../brakedust.github.io/
cp -r data/mhc-hockey/bt-elo ../brakedust.github.io/
cp -r data/mhc-hockey/bt-elo-movm ../brakedust.github.io/
cp -r data/mhc-hockey/bt-elo-movm-rev ../brakedust.github.io/