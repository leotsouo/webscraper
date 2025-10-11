
import streamlit as st
import pandas as pd
import pathlib, json, re
from datetime import datetime

st.set_page_config(page_title="Dual-Source Scraper — Dashboard", layout="wide")
st.title("Dual-Source Web Scraper — Streamlit 介面 (C)")

# ---------------------
# Paths (keep project defaults)
# ---------------------
snap_dir = pathlib.Path("data/snapshots")
diff_dir = pathlib.Path("data/diffs")
chart_dir = pathlib.Path("data/charts")

snap_dir.mkdir(parents=True, exist_ok=True)
diff_dir.mkdir(parents=True, exist_ok=True)
chart_dir.mkdir(parents=True, exist_ok=True)

# ---------------------
# Helpers
# ---------------------
def _read_csv_safe(path: pathlib.Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, dtype=str).fillna("")
    except Exception as e:
        st.error(f"讀取 CSV 失敗：{path} → {e}")
        return pd.DataFrame()
    # unify keys
    if "pk" not in df.columns and {"source","id"}.issubset(df.columns):
        df["pk"] = df["source"].astype(str) + "::" + df["id"].astype(str)
    return df

def _parse_date_col(df: pd.DataFrame) -> pd.DataFrame:
    if "date" in df.columns:
        # accept YYYYMMDD, YYYY-MM-DD, or other; coerce invalid to NaT
        def _to_dt(x:str):
            x = str(x).strip()
            for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
                try:
                    return datetime.strptime(x, fmt)
                except Exception:
                    pass
            return pd.NaT
        df["_date_dt"] = df["date"].map(_to_dt)
    return df

def _to_price_num(s: str) -> float:
    # keep digits and dot minus; e.g., "$1,234.50" -> 1234.50
    if s is None: return None
    s = str(s)
    m = re.findall(r"[-]?\d+(?:[.,]\d+)?", s.replace(",", ""))
    if not m: return None
    try:
        return float(m[0])
    except Exception:
        return None

def _ensure_price(df: pd.DataFrame) -> pd.DataFrame:
    col = "price" if "price" in df.columns else ("value" if "value" in df.columns else None)
    if col:
        df["_price_num"] = df[col].map(_to_price_num)
    return df

def _latest_snapshot_files() -> list[pathlib.Path]:
    return sorted(snap_dir.glob("snapshot_*.csv"))

def _latest_chart_images() -> list[pathlib.Path]:
    return sorted(chart_dir.glob("summary_*.png"))

# ---------------------
# Sidebar — source data & filters
# ---------------------
st.sidebar.header("資料來源與篩選")
snaps = _latest_snapshot_files()
if not snaps:
    st.sidebar.info("找不到快照（data/snapshots/snapshot_*.csv）。\n請先執行 CLI：\n\n`python -m src.interface.cli scrape ...`")
selected_snap = st.sidebar.selectbox("選擇快照檔", options=[s.name for s in snaps], index=len(snaps)-1 if snaps else 0)

df = pd.DataFrame()
if snaps:
    snap_path = snap_dir / selected_snap
    df = _read_csv_safe(snap_path)
    df = _parse_date_col(df)
    df = _ensure_price(df)

    # Basic search & filters
    keyword = st.sidebar.text_input("關鍵字（title / url / author / category）", "")
    source_opts = sorted(df["source"].unique()) if "source" in df.columns else []
    sel_sources = st.sidebar.multiselect("來源篩選", source_opts, default=source_opts)

    cat_opts = sorted([c for c in df.get("category", pd.Series([], dtype=str)).unique() if c])
    sel_cats = st.sidebar.multiselect("分類篩選（可留空）", cat_opts, default=cat_opts)

    # Date range filter if have dates
    if "_date_dt" in df.columns and df["_date_dt"].notna().any():
        dmin = pd.to_datetime(df["_date_dt"]).min()
        dmax = pd.to_datetime(df["_date_dt"]).max()
        drange = st.sidebar.date_input("日期區間", value=(dmin.date(), dmax.date()))
        if isinstance(drange, tuple) and len(drange) == 2:
            start_date, end_date = drange
        else:
            start_date, end_date = dmin.date(), dmax.date()
    else:
        start_date = end_date = None

    # Price range
    if "_price_num" in df.columns and df["_price_num"].notna().any():
        pmin = float(df["_price_num"].min())
        pmax = float(df["_price_num"].max())
        sel_pmin, sel_pmax = st.sidebar.slider("價格區間", min_value=float(pmin), max_value=float(pmax), value=(float(pmin), float(pmax)))
    else:
        sel_pmin = sel_pmax = None

    # Apply filters
    filtered = df.copy()
    if keyword:
        kw = keyword.lower()
        hay = pd.Series([""]*len(filtered))
        for c in ["title", "url", "author", "category"]:
            if c in filtered.columns:
                hay = hay + " " + filtered[c].astype(str).str.lower()
        mask_kw = hay.str.contains(kw, na=False)
        filtered = filtered[mask_kw]

    if "source" in filtered.columns and sel_sources:
        filtered = filtered[filtered["source"].isin(sel_sources)]

    if "category" in filtered.columns and sel_cats:
        filtered = filtered[filtered["category"].isin(sel_cats)]

    if start_date and end_date and "_date_dt" in filtered.columns:
        m = filtered["_date_dt"].dt.date.between(start_date, end_date)
        filtered = filtered[m]

    if sel_pmin is not None and sel_pmax is not None and "_price_num" in filtered.columns:
        m = filtered["_price_num"].between(sel_pmin, sel_pmax)
        filtered = filtered[m]

    # ---------------------
    # Top metrics
    # ---------------------
    left, mid, right = st.columns(3)
    left.metric("目前筆數 (過濾後)", len(filtered))
    mid.metric("來源數", len(filtered["source"].unique()) if "source" in filtered.columns else 0)
    right.metric("分類數", len([c for c in filtered.get("category", pd.Series([], dtype=str)).unique() if c]))

    # ---------------------
    # Charts (≥ 2)
    # ---------------------
    st.subheader("📊 快照視覺化")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("各來源筆數分佈")
        if "source" in filtered.columns:
            st.bar_chart(filtered["source"].value_counts().sort_values(ascending=False))
        else:
            st.info("無 source 欄。")

    with c2:
        if "_price_num" in filtered.columns and filtered["_price_num"].notna().sum() > 0:
            st.caption("價格分佈（Histogram）")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots()
            ax.hist(filtered["_price_num"].dropna().astype(float), bins=20)
            ax.set_xlabel("price")
            ax.set_ylabel("count")
            st.pyplot(fig)
        elif "category" in filtered.columns:
            st.caption("分類前十 (若無價格欄位)")
            st.bar_chart(filtered["category"].value_counts().head(10))
        else:
            st.info("無價格或分類欄可視覺化。")

    # Optional: time trend if date available
    if "_date_dt" in filtered.columns and filtered["_date_dt"].notna().any():
        st.caption("時間序列：各日期筆數")
        daily = filtered.copy()
        daily["_d"] = daily["_date_dt"].dt.date
        st.line_chart(daily["_d"].value_counts().sort_index())

    # ---------------------
    # Data table + download
    # ---------------------
    st.subheader("📄 資料表")
    show_cols = [c for c in ["source","id","title","url","author","category","date","price","value"] if c in filtered.columns]
    if "pk" in filtered.columns: show_cols = ["pk"] + show_cols
    st.dataframe(filtered[show_cols].reset_index(drop=True), use_container_width=True, height=350)
    st.download_button(
        "下載過濾後 CSV",
        data=filtered[show_cols].to_csv(index=False).encode("utf-8"),
        file_name="filtered_snapshot.csv",
        mime="text/csv"
    )

# ---------------------
# Diff summary & images
# ---------------------
st.subheader("Diff Summary（最新一次）")
summary_path = diff_dir / "summary.json"
if summary_path.exists():
    try:
        summary = json.loads(summary_path.read_text())
    except Exception as e:
        st.error(f"讀取 summary.json 失敗：{e}")
        summary = None

    if summary:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("新增 new", int(summary.get("new", 0)))
        m2.metric("刪除 deleted", int(summary.get("deleted", 0)))
        m3.metric("修改 changed", int(summary.get("changed", 0)))
        m4.metric("日期", summary.get("date", "-"))

        # show generated bar image (pipeline.diff.chart_summary)
        charts = _latest_chart_images()
        if charts:
            st.image(str(charts[-1]), caption=charts[-1].name, use_container_width=True)
        else:
            # fallback inline bar
            st.info("找不到 charts/summary_*.png，以下為即時生成的簡易長條圖：")
            df_bar = pd.DataFrame({
                "type": ["new", "deleted", "changed"],
                "count": [summary.get("new",0), summary.get("deleted",0), summary.get("changed",0)]
            })
            st.bar_chart(df_bar.set_index("type"))

        # Try to locate latest diff CSVs by stamp
        stamp = summary.get("date","")
        new_csv = diff_dir / f"diff_{stamp}_new.csv"
        del_csv = diff_dir / f"diff_{stamp}_deleted.csv"
        # changed is currently not saved as CSV by pipeline; list is in memory only.

        exp = st.expander("查看 New / Deleted 明細（若存在）")
        with exp:
            if new_csv.exists():
                st.caption(f"New: {new_csv.name}")
                st.dataframe(_read_csv_safe(new_csv), use_container_width=True, height=200)
            else:
                st.info("未找到對應的 new CSV。")

            if del_csv.exists():
                st.caption(f"Deleted: {del_csv.name}")
                st.dataframe(_read_csv_safe(del_csv), use_container_width=True, height=200)
            else:
                st.info("未找到對應的 deleted CSV。")
else:
    st.info("No diff summary yet. 請先執行 `python -m src.interface.cli diff ...` 後再回來看。")
