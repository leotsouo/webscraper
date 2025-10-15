import argparse, yaml, pandas as pd, pathlib, sys
from src.scraper.static_scraper import scrape_static
from src.scraper.dynamic_scraper import scrape_dynamic
from src.scraper.linetoday_dynamic import scrape as scrape_linetoday  # ← OK
from src.pipeline.clean import clean_df
from src.pipeline.storage import write_snapshot, latest_two_snapshots
from src.pipeline.diff import diff_snapshots, write_outputs, chart_summary
from datetime import datetime  # ← 你的 now_stamp 用得到，順手補上

def now_stamp():
    return datetime.now().strftime("%Y%m%d")

def load_cfg(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def scrape_cmd(args):
    cfg = load_cfg(args.config)
    frames = []
    for src in cfg["sources"]:
        if src["type"] == "static":
            df = scrape_static(src)
        elif src["type"] == "dynamic":
            # 這裡加名稱特判：LINE TODAY 走我們新寫的抓手
            if src.get("name") in {"linetoday_shallow", "linetoday_deep"}:
                print(f"[cli] using LINE TODAY scraper for source={src.get('name')}")
                df = scrape_linetoday(src)
            else:
                df = scrape_dynamic(src)  # 其他動態維持舊流程
        else:
            print(f"Unknown source type: {src['type']}", file=sys.stderr)
            continue
        frames.append(df)

    all_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    path = write_snapshot(all_df, args.out)
    print(f"Wrote raw snapshot: {path}")

def clean_cmd(args):
    p = pathlib.Path(args.snapshots)
    files = sorted(p.glob("snapshot_*.csv"))
    if not files:
        print("No snapshots found.", file=sys.stderr)
        sys.exit(1)
    latest = files[-1]
    df = pd.read_csv(latest)
    clean = clean_df(df)
    clean.to_csv(latest, index=False)
    print(f"Cleaned snapshot in place: {latest}")

def diff_cmd(args):
    prev, curr = latest_two_snapshots(args.snapshots)
    if not prev or not curr:
        print("Need at least two snapshots to diff.", file=sys.stderr)
        sys.exit(1)
    res = diff_snapshots(prev, curr)
    summary, summary_path = write_outputs(res, args.diffs)
    chart_path = chart_summary(summary, args.charts)
    print(f"Summary: {summary} \nWrote {summary_path} \nChart: {chart_path}")

def main():
    ap = argparse.ArgumentParser(prog="dual-source-webscraper")
    sub = ap.add_subparsers(required=True)

    ap_scrape = sub.add_parser("scrape", help="Scrape all configured sources into a new snapshot CSV")
    ap_scrape.add_argument("--config", required=True)
    ap_scrape.add_argument("--out", default="data/snapshots")
    ap_scrape.set_defaults(func=scrape_cmd)

    ap_clean = sub.add_parser("clean", help="Clean latest snapshot (normalize date/price, dedup, last_seen_at)")
    ap_clean.add_argument("--snapshots", default="data/snapshots")
    ap_clean.set_defaults(func=clean_cmd)

    ap_diff = sub.add_parser("diff", help="Diff latest two snapshots, write CSVs + summary.json + chart")
    ap_diff.add_argument("--snapshots", default="data/snapshots")
    ap_diff.add_argument("--diffs", default="data/diffs")
    ap_diff.add_argument("--charts", default="data/charts")
    ap_diff.set_defaults(func=diff_cmd)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
