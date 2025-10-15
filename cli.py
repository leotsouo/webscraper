import argparse
from datetime import datetime, timezone
from pathlib import Path

from pipelines.pchome_fetch import fetch_to_csv
from pipelines.diff import diff_snapshots

def _today_dir(base="data/snapshots") -> Path:
    return Path(base) / datetime.now(timezone.utc).strftime("%Y%m%d")

def main():
    ap = argparse.ArgumentParser(description="Webscraper CLI")
    sub = ap.add_subparsers(dest="cmd")

    ap_fetch = sub.add_parser("fetch", help="Fetch data from a source")
    ap_fetch.add_argument("source", choices=["pchome"], help="Data source")
    ap_fetch.add_argument("--q", required=True, help="Search keyword")
    ap_fetch.add_argument("--pages", type=int, default=5, help="Pages to fetch")

    ap_diff = sub.add_parser("diff", help="Diff two snapshots")
    ap_diff.add_argument("--prev", required=True, help="Path to previous snapshot CSV")
    ap_diff.add_argument("--curr", required=True, help="Path to current snapshot CSV")

    args = ap.parse_args()
    if args.cmd == "fetch":
        if args.source == "pchome":
            out_dir = _today_dir()
            out_csv = fetch_to_csv(q=args.q, pages=args.pages, outdir=str(out_dir))
            print(f"[OK] wrote {out_csv}")
    elif args.cmd == "diff":
        prev = Path(args.prev)
        curr = Path(args.curr)
        diff_csv, summary = diff_snapshots(prev, curr, out_dir=curr.parent)
        print(f"[OK] wrote {diff_csv}")
        print(f"[OK] wrote {summary}")
    else:
        ap.print_help()

if __name__ == "__main__":
    main()
