#!/usr/bin/env bash
set -euo pipefail

# Second+ run: scrape, clean, and diff against previous snapshot
python -m interface.cli scrape --config config/sources.yaml --out data/snapshots
python -m interface.cli clean --snapshots data/snapshots
python -m interface.cli diff --snapshots data/snapshots --diffs data/diffs --charts data/charts
echo "Incremental run complete. See data/diffs and data/charts."
