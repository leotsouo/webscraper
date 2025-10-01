import pandas as pd, json, pathlib, datetime as dt
import matplotlib.pyplot as plt

def load_csv(path: str) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str).fillna("")

def diff_snapshots(prev_path: str, curr_path: str):
    prev = load_csv(prev_path)
    curr = load_csv(curr_path)

    # 補 pk
    for df in (prev, curr):
        if "pk" not in df.columns and {"source","id"}.issubset(df.columns):
            df["pk"] = df["source"].astype(str) + "::" + df["id"].astype(str)

    prev_idx = prev.set_index("pk")
    curr_idx = curr.set_index("pk")

    new_keys = curr_idx.index.difference(prev_idx.index)
    del_keys = prev_idx.index.difference(curr_idx.index)
    common_keys = prev_idx.index.intersection(curr_idx.index)

    # 忽略這些會變動或不該作為內容差異的欄位
    ignore_cols = {"last_seen_at"}

    changed_rows = []
    for k in common_keys:
        a, b = prev_idx.loc[k], curr_idx.loc[k]
        diffs = {}
        for col in (set(curr.columns) & set(prev.columns)) - ignore_cols:
            if a.get(col, "") != b.get(col, ""):
                diffs[col] = {"old": a.get(col, ""), "new": b.get(col, "")}
        if diffs:
            changed_rows.append({"pk": k, "diffs": diffs})

    return {
        "new": curr_idx.loc[new_keys].reset_index(),
        "deleted": prev_idx.loc[del_keys].reset_index(),
        "changed": changed_rows
    }

def write_outputs(diff_res: dict, out_dir: str):
    out = pathlib.Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d")
    # write diff CSVs
    diff_res["new"].to_csv(out / f"diff_{stamp}_new.csv", index=False)
    diff_res["deleted"].to_csv(out / f"diff_{stamp}_deleted.csv", index=False)
    # summary.json
    summary = {
        "date": stamp,
        "new": int(len(diff_res["new"])),
        "deleted": int(len(diff_res["deleted"])),
        "changed": int(len(diff_res["changed"]))
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary, str(out / "summary.json")

def chart_summary(summary: dict, charts_dir: str):
    import matplotlib.pyplot as plt
    pathlib.Path(charts_dir).mkdir(parents=True, exist_ok=True)
    fig = plt.figure()  # single chart only; color defaults per policy
    labels = ["new", "deleted", "changed"]
    values = [summary.get("new",0), summary.get("deleted",0), summary.get("changed",0)]
    plt.bar(labels, values)
    plt.title(f"Diff Summary {summary.get('date','')}")
    plt.xlabel("Type"); plt.ylabel("Count")
    out_path = pathlib.Path(charts_dir) / f"summary_{summary.get('date','')}.png"
    fig.savefig(out_path, bbox_inches="tight", dpi=160)
    plt.close(fig)
    return str(out_path)
