# src/scraper/dynamic_scraper.py

import pandas as pd
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeoutError
from .utils import allowed_by_robots, polite_delay
from urllib.parse import urljoin
import time

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
BASE_DELAY = 1.0

def exponential_backoff(attempt: int, base_delay: float = BASE_DELAY) -> float:
    """指數退避: 1s, 2s, 4s, 8s..."""
    return base_delay * (2 ** (attempt - 1))

def navigate_with_retry(page: Page, url: str, max_retries: int = MAX_RETRIES):
    """
    Playwright 頁面導航 + 重試機制
    處理 429/5xx 錯誤和超時
    """
    last_exc = None
    
    for attempt in range(1, max_retries + 1):
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=30000)
            sc = resp.status if resp else 200
            
            # 檢查狀態碼
            if sc in RETRY_STATUSES:
                if attempt < max_retries:
                    # 檢查 Retry-After header
                    ra = resp.headers.get("retry-after") if resp else None
                    wait = float(ra) if ra else exponential_backoff(attempt)
                    
                    print(f"HTTP {sc} on {url}")
                    print(f"   Retry {attempt}/{max_retries} after {wait:.1f}s...")
                    time.sleep(wait)
                    continue
                else:
                    raise RuntimeError(f"HTTP {sc} after {max_retries} retries")
            
            return resp
            
        except PlaywrightTimeoutError as e:
            last_exc = e
            if attempt < max_retries:
                wait = exponential_backoff(attempt)
                print(f"Timeout on {url}")
                print(f"   Retry {attempt}/{max_retries} after {wait:.1f}s...")
                time.sleep(wait)
            else:
                raise
    
    if last_exc:
        raise last_exc

def extract_attr(el, attr):
    try:
        return el.get_attribute(attr) or ""
    except Exception:
        return ""

def _do_infinite_scroll(page, times=6, wait_ms=500):
    for _ in range(times):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
        page.wait_for_timeout(wait_ms)

def _scrape_items_from_page(page, source_cfg, base_url):
    elements = page.query_selector_all(source_cfg["item_selector"])
    rows = []

    for el in elements:
        row = {}
        for field, selector in source_cfg["fields"].items():
            if not selector:
                row[field] = ""
                continue
                
            if "@ " in selector or " @" in selector:
                css, attr = selector.split("@")
                node = el.query_selector(css.strip()) or page.query_selector(css.strip())
                row[field] = extract_attr(node, attr.strip()) if node else ""
            else:
                node = el.query_selector(selector) or page.query_selector(selector)
                row[field] = node.inner_text().strip() if node else ""
            
            if field == "url" and row[field]:
                row[field] = urljoin(base_url, row[field])
        
        row["source"] = source_cfg["name"]
        if not row.get("id"):
            row["id"] = row.get("url") or row.get("title")
        
        rows.append(row)
    
    return rows

def scrape_dynamic(source_cfg: dict) -> pd.DataFrame:
    url = source_cfg["list_url"]
    
    if not allowed_by_robots(url):
        raise RuntimeError(f"Blocked by robots.txt: {url}")
    
    all_rows = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 使用重試機制導航
        navigate_with_retry(page, url)
        
        # 無限捲動 (optional)
        scroll_cfg = source_cfg.get("infinite_scroll") or {}
        if scroll_cfg:
            _do_infinite_scroll(
                page,
                times=int(scroll_cfg.get("times", 6)),
                wait_ms=int(scroll_cfg.get("wait_ms", 500))
            )
        
        polite_delay()
        
        # 當前頁
        all_rows.extend(_scrape_items_from_page(page, source_cfg, url))
        
        # 翻頁處理
        pag = source_cfg.get("pagination") or {}
        next_sel = pag.get("next_selector")
        max_pages = int(pag.get("max_pages", 1))
        
        for _ in range(max_pages - 1):
            if not next_sel:
                break
            
            try:
                page.wait_for_selector(next_sel, timeout=3000)
                page.click(next_sel)
                page.wait_for_load_state("networkidle")
            except PlaywrightTimeoutError:
                break
            
            polite_delay()
            all_rows.extend(_scrape_items_from_page(page, source_cfg, url))
        
        browser.close()
    
    return pd.DataFrame(all_rows)
