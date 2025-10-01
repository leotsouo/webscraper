import streamlit as st, pandas as pd, pathlib, json

st.title("Dual-Source Web Scraper – Minimal Interface")

snap_dir = pathlib.Path("data/snapshots")
diff_dir = pathlib.Path("data/diffs")
chart_dir = pathlib.Path("data/charts")

st.subheader("Latest Snapshot")
snaps = sorted(snap_dir.glob("snapshot_*.csv"))
if snaps:
    latest = snaps[-1]
    st.write(f"Latest snapshot: {latest.name}")
    df = pd.read_csv(latest)
    q = st.text_input("Keyword search (title/url/author/category):", "")
    if q:
        mask = False
        for col in [c for c in df.columns if c in ["title","url","author","category"]]:
            mask = mask | df[col].fillna("").str.contains(q, case=False, na=False)
        st.dataframe(df[mask])
    else:
        st.dataframe(df.head(100))
else:
    st.info("No snapshots yet. Run the CLI first.")

st.subheader("Diff Summary")
summary_path = diff_dir / "summary.json"
if summary_path.exists():
    summary = json.loads(summary_path.read_text())
    st.json(summary)
    # show chart if exists
    charts = sorted(chart_dir.glob("summary_*.png"))
    if charts:
        st.image(str(charts[-1]))
else:
    st.info("No diff summary yet. Run incremental diff.")
