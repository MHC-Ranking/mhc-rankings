#!/bin/bash
# Rebuild the Colley rankings for every division that has a games file.
set -e

for games in \
    mhc-results/varsity2026-27/v-game-results_2026-27.tsv \
    mhc-results/jv2026-27/jv-game-results_2026-27.tsv \
    mhc-results/varsity2025-26/v-game-results_2025-26.tsv; do
    if [ -f "$games" ]; then
        echo "Generating rankings for $games..."
        uv run mhc-rankings --input "$games" --output-dir "$(dirname "$games")/rankings"
    else
        echo "Skipping $games (no games file yet)."
    fi
done

echo "Done!"
