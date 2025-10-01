# 1) 啟用 venv
. .\.venv\Scripts\Activate.ps1

# 2) 再跑一次：抓 -> 清
python -m src.interface.cli scrape --config config/sources.yaml --out data/snapshots
python -m src.interface.cli clean --snapshots data/snapshots

# 3) 做差異 + 輸出圖表
python -m src.interface.cli diff --snapshots data/snapshots --diffs data/diffs --charts data/charts

# 4) 顯示摘要
type data\diffs\summary.json
