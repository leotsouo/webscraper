# 1) 啟用 venv（請先建立好 .venv）
. .\.venv\Scripts\Activate.ps1

# 2) 第一次跑：抓 -> 清
python -m src.interface.cli scrape --config config/sources.yaml --out data/snapshots
python -m src.interface.cli clean --snapshots data/snapshots

# 3) 簡單檢查
python -c "import pandas as pd, pathlib; p=sorted(pathlib.Path('data/snapshots').glob('snapshot_*.csv'))[-1]; df=pd.read_csv(p); print('rows=',len(df)); print(df['source'].value_counts().to_dict())"
