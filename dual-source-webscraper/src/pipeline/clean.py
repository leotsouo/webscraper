import pandas as pd, re
from dateutil import parser as dtparser

def normalize_date(v: str) -> str:
    if not v: return ""
    try:
        d = dtparser.parse(v, dayfirst=False, yearfirst=True)
        return d.strftime("%Y%m%d")
    except Exception:
        # try numeric YYYYMMDD already
        if re.fullmatch(r"\d{8}", v): return v
        return ""

def to_number(v: str) -> float | None:
    if v is None: return None
    s = re.sub(r"[^0-9.\-]", "", str(v))
    try:
        return float(s)
    except Exception:
        return None

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    # Normalize columns that might exist
    if "date" in df.columns:
        df["date"] = df["date"].map(normalize_date)
    if "price" in df.columns:
        df["price"] = df["price"].map(to_number)
    # create composite key
    if "source" in df.columns and "id" in df.columns:
        df["pk"] = df["source"].astype(str) + "::" + df["id"].astype(str)
        df = df.drop_duplicates(subset=["pk"])
    # last_seen_at
    df["last_seen_at"] = pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    return df
