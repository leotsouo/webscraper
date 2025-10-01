import pandas as pd, tempfile, os
from src.pipeline.diff import diff_snapshots, write_outputs

def _save(df, path):
    df.to_csv(path, index=False)

def test_diff_basic(tmp_path):
    prev = tmp_path / "prev.csv"
    curr = tmp_path / "curr.csv"

    df_prev = pd.DataFrame([
        {"source":"s","id":"1","title":"A","pk":"s::1"},
        {"source":"s","id":"2","title":"B","pk":"s::2"},
    ])
    df_curr = pd.DataFrame([
        {"source":"s","id":"2","title":"B2","pk":"s::2"},   # changed
        {"source":"s","id":"3","title":"C","pk":"s::3"},    # new
    ])
    _save(df_prev, prev); _save(df_curr, curr)
    res = diff_snapshots(str(prev), str(curr))
    assert len(res["new"]) == 1
    assert len(res["deleted"]) == 1
    assert len(res["changed"]) == 1
