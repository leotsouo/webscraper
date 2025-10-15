#!/usr/bin/env bash
set -euo pipefail

# 第二次跑：先再抓一次，然後做 diff
python cli.py fetch pchome --q "iphone 15" --pages 6

# 自動找最近兩天資料夾做 diff（簡化用；正式可改成手動指定）
BASE="data/snapshots"
LAST2=($(ls -1 ${BASE} | sort | tail -n 2))
PREV="${BASE}/${LAST2[0]}/pchome.csv"
CURR="${BASE}/${LAST2[1]}/pchome.csv"

python cli.py diff --prev "$PREV" --curr "$CURR"
