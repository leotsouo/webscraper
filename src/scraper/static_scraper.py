# src/scraper/static_scraper.py
import requests, pandas as pd
from bs4 import BeautifulSoup
from .utils import allowed_by_robots, polite_delay
from urllib.parse import urljoin

def extract_text(el):
    return el.get_text(strip=True) if el else ""

def get_attr(soup, selector, attr=None):
    if not selector:
        return ""
    if "@ " in selector or " @" in selector:
        css, attr = selector.split("@")
        css, attr = css.strip(), attr.strip()
    else:
        css = selector
    node = soup.select_one(css)
    if not node:
        return ""
    return node.get(attr, "") if attr else extract_text(node)

def _scrape_one_page(page_url: str, source_cfg: dict, session: requests.Session):
    resp = session.get(page_url, timeout=20)
    resp.raise_for_status()
    polite_delay()

    soup = BeautifulSoup(resp.text, "lxml")
    items = soup.select(source_cfg["item_selector"])
    rows = []
    for it in items:
        row = {}
        for field, selector in source_cfg["fields"].items():
            val = get_attr(it, selector)
            if field == "url" and val:
                # 連結要**相對當前頁**做 urljoin，否則翻頁後會錯
                val = urljoin(page_url, val)
            row[field] = val
        row["source"] = source_cfg["name"]
        # 後備 id：若沒有穩定 id，就用 URL（最穩），再不行用 title
        if not row.get("id"):
            row["id"] = row.get("url") or row.get("title") or ""
        rows.append(row)
    return rows, soup

def scrape_static(source_cfg: dict) -> pd.DataFrame:
    start_url = source_cfg["list_url"]
    if not allowed_by_robots(start_url):
        raise RuntimeError(f"Blocked by robots.txt: {start_url}")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                      " AppleWebKit/537.36 (KHTML, like Gecko)"
                      " Chrome/124.0 Safari/537.36"
    })

    all_rows = []
    page_url = start_url
    max_pages = int(source_cfg.get("pagination", {}).get("max_pages", 1))
    next_sel = source_cfg.get("pagination", {}).get("next_selector")

    for _ in range(max_pages):
        rows, soup = _scrape_one_page(page_url, source_cfg, session)
        all_rows.extend(rows)

        # 沒設定分頁或找不到下一頁就收工
        if not next_sel:
            break
        next_node = soup.select_one(next_sel)
        if not next_node:
            break
        href = next_node.get("href", "")
        if not href:
            break
        page_url = urljoin(page_url, href)  # 以**當前頁**為基準拼下一頁

    return pd.DataFrame(all_rows)
