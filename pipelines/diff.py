import csv
import json
from pathlib import Path
from typing import Dict, List

def _load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def diff_snapshots(prev_csv: Path, curr_csv: Path, out_dir: Path):
    prev_rows = _load_csv(prev_csv)
    curr_rows = _load_csv(curr_csv)

    prev = {r["id"]: r for r in prev_rows if r.get("id")}
    curr = {r["id"]: r for r in curr_rows if r.get("id")}

    new_ids = [i for i in curr if i not in prev]
    del_ids = [i for i in prev if i not in curr]
    changed_ids = []
    for i in curr:
        if i in prev:
            # 以 price 或 available 異動視為 changed；可依需求擴充
            if (prev[i].get("price") != curr[i].get("price")
                or prev[i].get("available") != curr[i].get("available")):
                changed_ids.append(i)

    out_dir.mkdir(parents=True, exist_ok=True)
    diff_csv = out_dir / f"diff_{curr_csv.parent.name}.csv"
    with diff_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["type", "id"])
        for i in new_ids: w.writerow(["new", i])
        for i in del_ids: w.writerow(["deleted", i])
        for i in changed_ids: w.writerow(["changed", i])

    summary = {
        "source": "pchome",
        "new": len(new_ids),
        "deleted": len(del_ids),
        "changed": len(changed_ids)
    }
    summary_path = out_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    return diff_csv, summary_path
