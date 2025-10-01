import argparse, yaml, pandas as pd, pathlib, sys
from datetime import datetime
from scraper.static_scraper import scrape_static
from scraper.dynamic_scraper import scrape_dynamic
from pipeline.clean import clean_df
from pipeline.storage import write_snapshot, latest_two_snapshots
from pipeline.diff import diff_snapshots, write_outputs, chart_summary

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
            df = scrape_dynamic(src)
        else:
            print(f"Unknown source type: {src['type']}", file=sys.stderr); continue
        frames.append(df)
    all_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    # write raw snapshot pre-clean (optional) or proceed directly to clean in next step
    path = write_snapshot(all_df, args.out)
    print(f"Wrote raw snapshot: {path}")

def clean_cmd(args):
    p = pathlib.Path(args.snapshots)
    files = sorted(p.glob("snapshot_*.csv"))
    if not files:
        print("No snapshots found.", file=sys.stderr); sys.exit(1)
    latest = files[-1]
    df = pd.read_csv(latest)
    clean = clean_df(df)
    clean.to_csv(latest, index=False)
    print(f"Cleaned snapshot in place: {latest}")

def diff_cmd(args):
    prev, curr = latest_two_snapshots(args.snapshots)
    if not prev or not curr:
        print("Need at least two snapshots to diff.", file=sys.stderr); sys.exit(1)
    res = diff_snapshots(prev, curr)
    summary, summary_path = write_outputs(res, args.diffs)
    chart_path = chart_summary(summary, args.charts)
    print(f"Summary: {summary} \nWrote {summary_path} \nChart: {chart_path}")

def main():
    ap = argparse.ArgumentParser(prog="dual-source-webscraper")
    sub = ap.add_subparsers(required=True)

    # scrape
    ap_scrape = sub.add_parser("scrape", help="Scrape all configured sources into a new snapshot CSV")
    ap_scrape.add_argument("--config", required=True)
    ap_scrape.add_argument("--out", default="data/snapshots")
    ap_scrape.set_defaults(func=scrape_cmd)

    # clean
    ap_clean = sub.add_parser("clean", help="Clean latest snapshot (normalize date/price, dedup, last_seen_at)")
    ap_clean.add_argument("--snapshots", default="data/snapshots")
    ap_clean.set_defaults(func=clean_cmd)

    # diff
    ap_diff = sub.add_parser("diff", help="Diff latest two snapshots, write CSVs + summary.json + chart")
    ap_diff.add_argument("--snapshots", default="data/snapshots")
    ap_diff.add_argument("--diffs", default="data/diffs")
    ap_diff.add_argument("--charts", default="data/charts")
    ap_diff.set_defaults(func=diff_cmd)

    args = ap.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
