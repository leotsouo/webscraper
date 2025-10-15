from datetime import datetime, timezone
from pathlib import Path
import csv
from typing import Dict, Any, List

from sources.pchome_client import PChomeClient

FIELDS = [
    "id", "source", "title", "url", "vendor",
    "category", "price", "date", "last_seen_at", "available"
]

def _now_yyyymmdd() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d")

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def normalize_item(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    把 PChome 搜尋回傳的商品欄位，對齊我們內部 schema。
    - 不同介面鍵名略有差異，這裡做多路徑 fallback。
    """
    # id 可能叫 Id / Id2 / ProdId，依實測而定；先保留多條路徑
    prod_id = (
        raw.get("Id")
        or raw.get("Id2")
        or raw.get("prod_id")
        or raw.get("ProdId")
        or raw.get("Id3")
        or ""
    )
    title = raw.get("Name") or raw.get("name") or raw.get("title") or ""
    brand = raw.get("Brand") or raw.get("V") or raw.get("brand") or ""
    cate = raw.get("CateName") or raw.get("cate") or raw.get("Cat") or ""
    price = None
    # 常見兩種：Price: {"P": int} 或 price: int
    if isinstance(raw.get("Price"), dict) and "P" in raw["Price"]:
        price = raw["Price"]["P"]
    elif "price" in raw:
        price = raw["price"]

    # 銷售狀態/是否可購買（先留空，之後可用 prod_status() 回填）
    available = raw.get("SaleStatus") or raw.get("available") or ""

    url = f"https://24h.pchome.com.tw/prod/{prod_id}" if prod_id else raw.get("Url") or ""

    return {
        "id": prod_id,
        "source": "pchome",
        "title": title,
        "url": url,
        "vendor": brand,
        "category": cate,
        "price": int(price) if isinstance(price, (int, str)) and str(price).isdigit() else None,
        "date": _now_yyyymmdd(),
        "last_seen_at": _now_iso(),
        "available": available,
    }

def fetch_to_csv(q: str, pages: int, outdir: str):
    """
    以關鍵字 + 分頁抓取，輸出到 snapshots/{YYYYMMDD}/pchome.csv
    """
    client = PChomeClient()
    items: List[Dict[str, Any]] = []

    for p in range(1, max(1, pages) + 1):
        page_json = client.search_page(q=q, page=p)
        prods = page_json.get("prods") or page_json.get("ProdList") or []
        if not isinstance(prods, list):
            prods = []
        items.extend(prods)
            # 正規化前做個提示，避免空檔害你以為有抓到
        if not items:
            raise RuntimeError("Search returned 0 items. 請換個關鍵字、調頁數，或打開 DevTools 檢查實際 XHR 端點。")

    # 正規化 & 去重（以 id 為主鍵）
    norm = [normalize_item(x) for x in items]
    dedup, seen = [], set()
    for r in norm:
        if r["id"] and r["id"] not in seen:
            seen.add(r["id"])
            dedup.append(r)

    out_dir = Path(outdir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = out_dir / "pchome.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in dedup:
            w.writerow(row)
    return out_csv
