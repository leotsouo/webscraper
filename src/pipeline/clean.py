import pandas as pd, re, math
from dateutil import parser as dtparser

def _is_nan(v) -> bool:
    try:
        return v is None or (isinstance(v, float) and math.isnan(v))
    except Exception:
        return False

def normalize_date(v) -> str:
    """
    將各種日期字串正規化為 YYYYMMDD。
    對於 None / NaN / 非字串都安全處理，無法解析則回傳空字串。
    """
    if _is_nan(v):
        return ""
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none", "null"}:
        return ""
    # 若本來就是 8 碼數字，直接接受
    if re.fullmatch(r"\d{8}", s):
        return s
    # 嘗試解析其他常見格式
    try:
        d = dtparser.parse(s, dayfirst=False, yearfirst=True)
        return d.strftime("%Y%m%d")
    except Exception:
        return ""

def to_number(v):
    """
    將價格/數值欄位轉成 float；空值或無法解析則回 None。
    """
    if _is_nan(v):
        return None
    s = str(v)
    # 只保留數字、小數點與負號
    s = re.sub(r"[^0-9.\-]", "", s)
    if s in {"", "-", ".", "-.", ".-"}:
        return None
    try:
        return float(s)
    except Exception:
        return None

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df if df is not None else pd.DataFrame()

    df = df.copy()  # ← 關鍵 1：避免在 view 上改

    # 確保必要欄位存在
    for col in ["source", "id", "title", "url", "author", "category", "date", "price"]:
        if col not in df.columns:
            df[col] = ""

    # 正規化
    df["date"] = df["date"].map(normalize_date)
    df["price"] = df["price"].map(to_number)

    # 複合主鍵、去重
    df["pk"] = df["source"].astype(str) + "::" + df["id"].astype(str)
    df = df.drop_duplicates(subset=["pk"]).copy()  # ← 關鍵 2：再 copy 一次

    # last_seen_at（用 loc 指派）
    df.loc[:, "last_seen_at"] = pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")  # ← 關鍵 3
    return df

