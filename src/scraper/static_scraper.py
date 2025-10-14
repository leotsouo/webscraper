# src/scraper/static_scraper.py

import requests
import pandas as pd
from bs4 import BeautifulSoup
from .utils import allowed_by_robots, polite_delay
from .http_client import get_with_retry  #  確保這行正確
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
    # 使用帶重試機制的 get_with_retry
    resp = get_with_retry(page_url, session=session, user_agent="WebScraperBot/1.0")
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
                val = urljoin(page_url, val)
            
            row[field] = val
        
        row["source"] = source_cfg["name"]
        
        if not row.get("id"):
            row["id"] = row.get("url") or row.get("title") or ""
        
        rows.append(row)
    
    return rows, soup

def scrape_static(source_cfg: dict) -> pd.DataFrame:
    start_url = source_cfg["list_url"]
    
    # robots.txt 檢查
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
        
        if not next_sel:
            break
        
        next_node = soup.select_one(next_sel)
        if not next_node:
            break
        
        href = next_node.get("href", "")
        if not href:
            break
        
        page_url = urljoin(page_url, href)
    
    return pd.DataFrame(all_rows)
