# src/scraper/dynamic_scraper.py
import pandas as pd
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import time

# ───────── utils ─────────
def _abs_url(u: str, prefix: str | None) -> str:
    if not u:
        return ""
    if urlparse(u).netloc:
        return u
    return urljoin(prefix, u) if prefix else u

def _norm(s: str) -> str:
    return " ".join((s or "").split())

def _paths(x):
    if isinstance(x, dict) and "any" in x:
        return x["any"] or []
    if isinstance(x, str) and x:
        return [x]
    return []

def _click_any(page, selectors, timeout_ms=5000):
    if not selectors:
        return False
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            btn.wait_for(state="visible", timeout=timeout_ms)
            btn.click()
            return True
        except Exception:
            continue
    return False

def _do_consent(page, cfg: dict | None):
    if not cfg:
        return
    _click_any(page, cfg.get("click_selector_any", []), cfg.get("timeout_ms", 5000))

def _do_load_more(page, cfg: dict | None):
    if not cfg:
        return
    sels = cfg.get("click_selector_any", [])
    times = int(cfg.get("times", 0))
    pause = int(cfg.get("pause_ms", 800))
    for _ in range(times):
        clicked = _click_any(page, sels, 3000)
        if not clicked:
            break
        page.wait_for_timeout(pause)

def _do_scroll(page, cfg: dict | None, item_selectors: list[str]):
    if not cfg:
        return
    times = int(cfg.get("times", 0))
    pause = int(cfg.get("pause_ms", 800))
    until_new = cfg.get("until_new_items")

    def count_items():
        counts = []
        for sel in item_selectors or []:
            try:
                counts.append(page.locator(sel).count())
            except Exception:
                counts.append(0)
        return max(counts) if counts else 0

    prev = count_items()
    for _ in range(times):
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(pause)
        curr = count_items()
        if until_new and (curr - prev) < int(until_new):
            break
        prev = curr

def _paginate_next(page, next_selector: str, max_pages: int):
    # 舊式「下一頁」翻頁（quotes.js）
    for _ in range(max_pages - 1):
        try:
            nxt = page.locator(next_selector).first
            nxt.wait_for(state="visible", timeout=3000)
            nxt.click()
            page.wait_for_load_state("domcontentloaded")
        except Exception:
            break

def _extract(page, cfg: dict) -> list[dict]:
    item_selector_any = cfg.get("item_selector_any")
    item_selector = cfg.get("item_selector")  # 兼容舊寫法
    fields = cfg.get("fields", {})
    post = cfg.get("postprocess", {})

    # 選擇命中最多的 item selector
    chosen_sel, chosen_cnt = None, -1
    sels = item_selector_any if item_selector_any else ([item_selector] if item_selector else [])
    for sel in sels:
        try:
            c = page.locator(sel).count()
            if c > chosen_cnt:
                chosen_sel, chosen_cnt = sel, c
        except Exception:
            pass
    if not chosen_sel:
        return []

    def get_text(node, css_list):
        for s in css_list:
            try:
                v = node.locator(s).first
                txt = v.text_content() or ""
                if txt.strip():
                    return txt.strip()
            except Exception:
                pass
        return ""

    def get_attr(node, css_list, attr):
        for s in css_list:
            try:
                v = node.locator(s).first
                val = v.get_attribute(attr)
                if val:
                    return val.strip()
            except Exception:
                pass
        return ""

    prefix = post.get("make_url_absolute_with_prefix")
    norm_keys = set(post.get("normalize_whitespace", []))
    dedup_key = tuple(post.get("dedup_key", [])) or ("id",)

    out, seen = [], set()
    nodes = page.locator(chosen_sel)
    n = nodes.count()
    for i in range(n):
        node = nodes.nth(i)

        # id: 允許 data-article-id 或 href 兩種
        id_val = ""
        for s in _paths(fields.get("id")):
            v = node.locator(s).first
            # 試 data-article-id
            try:
                val = v.get_attribute("data-article-id")
                if val:
                    id_val = val.strip()
                    break
            except Exception:
                pass
            # 試 href
            try:
                val = v.get_attribute("href")
                if val:
                    id_val = val.strip()
                    break
            except Exception:
                pass

        title = get_text(node, _paths(fields.get("title")))
        url = get_attr(node, _paths(fields.get("url")), "href")
        url = _abs_url(url, prefix)
        author = get_text(node, _paths(fields.get("author")))
        category = get_text(node, _paths(fields.get("category")))
        date = get_attr(node, _paths(fields.get("date")), "datetime") or \
               get_text(node, _paths(fields.get("date")))
        price = get_text(node, _paths(fields.get("price")))

        rec = {
            "id": id_val or url,
            "title": title,
            "url": url,
            "author": author,
            "category": category,
            "date": date,
            "price": price,
        }
        for k in norm_keys:
            rec[k] = _norm(rec.get(k, ""))

        key = tuple(rec.get(k, "") for k in dedup_key)
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out

def scrape_dynamic(source_cfg: dict) -> pd.DataFrame:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(source_cfg["list_url"], wait_until="domcontentloaded")

        if source_cfg.get("pagination", {}).get("next_selector"):
            # 舊式翻頁
            next_sel = source_cfg["pagination"]["next_selector"]
            max_p = int(source_cfg["pagination"].get("max_pages", 1))
            _paginate_next(page, next_sel, max_p)
        else:
            # 新式（LINE TODAY）：可選的彈窗 + 連點載入更多 + 滾動
            _do_consent(page, source_cfg.get("consent"))
            _do_load_more(page, source_cfg.get("load_more"))
            _do_scroll(page, source_cfg.get("scroll"), source_cfg.get("item_selector_any", []))

        items = _extract(page, source_cfg)
        browser.close()

    df = pd.DataFrame(items)
    # 讓 cleaner 安心
    for col in ["source", "id", "title", "url", "author", "category", "date", "price"]:
        if col not in df.columns:
            df[col] = ""
    df["source"] = source_cfg.get("name", df.get("source", ""))
    return df
