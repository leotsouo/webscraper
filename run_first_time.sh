#!/usr/bin/env bash
set -euo pipefail

# First snapshot run
python -m interface.cli scrape --config config/sources.yaml --out data/snapshots
python -m interface.cli clean --snapshots data/snapshots
# No diff on very first run
echo "First run complete. Snapshot written to data/snapshots/."
