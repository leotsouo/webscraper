import pandas as pd, datetime as dt, pathlib

def today_stamp():
    return dt.datetime.now().strftime("%Y%m%d")

def write_snapshot(df: pd.DataFrame, out_dir: str) -> str:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"snapshot_{today_stamp()}.csv"
    df.to_csv(path, index=False)
    return str(path)

def latest_two_snapshots(snap_dir: str):
    p = pathlib.Path(snap_dir)
    files = sorted(p.glob("snapshot_*.csv"))
    if len(files) < 2: return None, None
    return str(files[-2]), str(files[-1])
