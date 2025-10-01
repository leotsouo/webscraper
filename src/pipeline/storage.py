import pandas as pd, datetime as dt, pathlib

def today_stamp():
    # 保留原本的日戳：YYYYMMDD
    return dt.datetime.now().strftime("%Y%m%d")

def write_snapshot(df: pd.DataFrame, out_dir: str) -> str:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # 新增時間到秒，避免同一天覆蓋：YYYYMMDD_HHMMSS
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = out / f"snapshot_{ts}.csv"
    df.to_csv(path, index=False)
    return str(path)

def latest_two_snapshots(snap_dir: str):
    p = pathlib.Path(snap_dir)
    files = sorted(p.glob("snapshot_*.csv"))
    if len(files) < 2: return None, None
    return str(files[-2]), str(files[-1])
