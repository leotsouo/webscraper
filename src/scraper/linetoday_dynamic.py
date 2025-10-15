# src/scraper/linetoday_dynamic.py
import pandas as pd
from urllib.parse import urljoin, urlparse
from playwright.sync_api import sync_playwright

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
            btn.click(no_wait_after=True)  # 避免被導走
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
    pause = int(cfg.get("pause_ms", 900))
    for _ in range(times):
        clicked = _click_any(page, sels, 3000)
        if not clicked or page.is_closed():
            break
        page.wait_for_timeout(pause)

def _do_scroll(page, cfg: dict | None, item_selectors: list[str]):
    if not cfg or page.is_closed():
        return
    times = int(cfg.get("times", 0))
    pause = int(cfg.get("pause_ms", 900))
    until_new = cfg.get("until_new_items")

    def count_items():
        try:
            counts = []
            for sel in item_selectors or []:
                counts.append(page.locator(sel).count())
            return max(counts) if counts else 0
        except Exception:
            return 0

    prev = count_items()
    for _ in range(times):
        if page.is_closed():
            break
        try:
            page.mouse.wheel(0, 24000)  # 比 evaluate 更不易炸
        except Exception:
            break
        page.wait_for_timeout(pause)
        curr = count_items()
        if until_new and (curr - prev) < int(until_new):
            break
        prev = curr
    try:
        counts = {sel: page.locator(sel).count() for sel in (item_selectors or [])}
        print(f"[linetoday] after scroll, candidate counts = {counts}")
    except Exception as e:
        print(f"[linetoday] count items error: {e}")

def _keep_alive(context, page, url):
    """若 page 被關/被帶走，就新開一頁導回列表；否則原樣返回。"""
    try:
        if page is None or page.is_closed():
            p = context.new_page()
            p.goto(url, wait_until="domcontentloaded")
            return p
        return page
    except Exception:
        p = context.new_page()
        p.goto(url, wait_until="domcontentloaded")
        return p


# ───────── developer helper：把候選節點輸出成 HTML 樣本 ─────────
def _dump_samples(page, selectors, out_html="data/debug/linetoday_items_sample.html"):
    try:
        import os
        os.makedirs("data/debug", exist_ok=True)
        parts = []
        parts.append("<style>pre{white-space:pre-wrap;border:1px solid #ddd;padding:8px;border-radius:6px}</style>")
        for sel in selectors:
            try:
                loc = page.locator(sel)
                n = min(loc.count(), 10)  # 每個 selector 取前 10 筆
                parts.append(f"<h3>Selector: <code>{sel}</code> (showing {n})</h3>")
                for i in range(n):
                    node = loc.nth(i)
                    html = node.evaluate("n => n.outerHTML")
                    parts.append(f"<pre>{html}</pre>")
            except Exception as e:
                parts.append(f"<p>Selector error: {sel} → {e}</p>")
        with open(out_html, "w", encoding="utf-8") as fp:
            fp.write("\n".join(parts))
        print(f"[linetoday] wrote samples -> {out_html}")
    except Exception as e:
        print(f"[linetoday] dump samples failed: {e}")

# ───────── 核心抽取 ─────────
def _extract(page, cfg: dict) -> list[dict]:
    # 若 YAML 沒提供，給一組通用候選
    item_selector_any = cfg.get("item_selector_any") or [
        "a[data-article-id]",
        "a[href*='/tw/v3/article/']",
        "a[href*='/article/']",
        "[role='article'] a[href]",
    ]
    fields = cfg.get("fields", {})
    post = cfg.get("postprocess", {})

    # 用「有效文章 href 數量」來挑 selector（只認 /article/）
    def _valid_href_count(sel: str) -> int:
        try:
            nodes = page.locator(sel)
            n = nodes.count()
            cnt = 0
            for i in range(n):
                href = (nodes.nth(i).get_attribute("href") or "")
                if "/article/" in href:
                    cnt += 1
            return cnt
        except Exception:
            return 0

    best_sel, best_cnt = None, -1
    for sel in item_selector_any:
        c = _valid_href_count(sel)
        print(f"[linetoday] selector '{sel}' valid-article-href count = {c}")
        if c > best_cnt:
            best_sel, best_cnt = sel, c

    # Fallback：完全抓不到就用全站 anchor 過濾
    if best_cnt <= 0:
        print("[linetoday] no valid article anchors via selectors; using fallback")
        anchors = page.locator("a[href*='/tw/v3/article/'], a[href*='/article/'], a[href*='/detail/']")
        n = anchors.count()
        out = []
        prefix = post.get("make_url_absolute_with_prefix", "https://today.line.me")
        for i in range(n):
            a = anchors.nth(i)
            href = a.get_attribute("href") or ""
            if "/article/" not in href:
                continue
            text = (a.text_content() or "").strip()
            title = a.get_attribute("title") or text
            url = _abs_url(href, prefix)
            if not url:
                continue
            out.append({
                "id": url,
                "title": title,
                "url": url,
                "author": "",
                "category": "",
                "date": "",
                "price": "",
            })
        print(f"[linetoday] fallback yielded {len(out)} items")
        return out

    # ── 正常路徑：用 best_sel 並過濾非 /article/ 連結 ──
    prefix = post.get("make_url_absolute_with_prefix", "https://today.line.me")
    norm_keys = set(post.get("normalize_whitespace", []))
    dedup_key = tuple(post.get("dedup_key", [])) or ("id",)

    def get_text(node, css_list):
        for s in css_list:
            try:
                if s == ":scope":
                    txt = node.text_content() or ""
                    if txt.strip():
                        return txt.strip()
                    continue
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
                if s == ":scope":
                    val = node.get_attribute(attr)
                    if val:
                        return val.strip()
                    continue
                v = node.locator(s).first
                val = v.get_attribute(attr)
                if val:
                    return val.strip()
            except Exception:
                pass
        return ""


    out, seen = [], set()
    nodes = page.locator(best_sel)
    n = min(nodes.count(), 120)  # 安全上限，避免極端情況拖太久
    print(f"[linetoday] extracting from best_sel with n={n}")
    for i in range(n):
        node = nodes.nth(i)
        raw_href = node.get_attribute("href") or ""
        if "/article/" not in raw_href:
            continue  # 只收文章連結

        # id: 先試 data-article-id，再退 href
        id_val = ""
        for s in _paths(fields.get("id")):
            try:
                v = node.locator(s).first
                val = v.get_attribute("data-article-id")
                if val:
                    id_val = val.strip(); break
            except Exception:
                pass
            try:
                v = node.locator(s).first
                val = v.get_attribute("href")
                if val:
                    id_val = val.strip(); break
            except Exception:
                pass

        title = get_text(node, _paths(fields.get("title")))
        url   = _abs_url(raw_href or get_attr(node, _paths(fields.get("url")), "href"), prefix)
        author   = get_text(node, _paths(fields.get("author")))
        category = get_text(node, _paths(fields.get("category")))
        date     = get_attr(node, _paths(fields.get("date")), "datetime") or \
                   get_text(node, _paths(fields.get("date")))
        price    = get_text(node, _paths(fields.get("price")))

        rec = {
            "id": (id_val or url),
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
        if key in seen or not rec["url"]:
            continue
        seen.add(key)
        out.append(rec)
        if (i+1) % 20 == 0:
            print(f"[linetoday] extracted {i+1}/{n}")
    print(f"[linetoday] extract done, total={len(out)}")
    return out

# ───────── 主流程 ─────────
def scrape(source_cfg: dict) -> pd.DataFrame:
    """同步 Playwright，專抓 LINE TODAY；回傳 DataFrame（欄位齊全給 cleaner 用）"""
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False, slow_mo=300)  # 除錯中；穩定後改 True
        context = browser.new_context(locale="zh-TW", viewport={"width": 1280, "height": 900})

        # 用 context 層級掛 init script（比 page 穩）
        try:
            context.add_init_script("""
            document.addEventListener('click', function(e){
              const a = e.target.closest('a');
              if (!a) return;
              a.removeAttribute('target'); // 禁止新分頁
            }, true);
            """)
        except Exception:
            pass

        page = context.new_page()
        page.set_default_timeout(4000)  # 所有 locator 操作最長 4s，避免卡住
        # 只關「從主頁彈出」的 popup；不要用 context.on('page')
        def _autoclose_popup(p):
            try:
                print(f"[linetoday] autoclose popup: {p.url}")
                p.close()
            except Exception:
                pass
        page.on("popup", _autoclose_popup)

        page.goto(source_cfg["list_url"], wait_until="domcontentloaded")
        # CSR：等一個 networkidle，讓主要 XHR 跑完
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        # 等任一合理文章 selector 出現（最多 12 秒）
        for sel in ["a[data-article-id]", "a[href*='/article/']", "[role='article'] a[href]"]:
            try:
                page.wait_for_selector(sel, timeout=4000, state="visible")
                break
            except Exception:
                continue

        _do_consent(page, source_cfg.get("consent"))
        page = _keep_alive(context, page, source_cfg["list_url"])

        _do_load_more(page, source_cfg.get("load_more"))
        page = _keep_alive(context, page, source_cfg["list_url"])

        _do_scroll(page, source_cfg.get("scroll"), source_cfg.get("item_selector_any", []))
        page = _keep_alive(context, page, source_cfg["list_url"])

        # 除錯快照
        page.wait_for_timeout(800)
        try:
            import os
            os.makedirs("data/debug", exist_ok=True)
            page.screenshot(path="data/debug/linetoday_after_scroll.png", full_page=True)
            with open("data/debug/linetoday_after_scroll.html", "w", encoding="utf-8") as fp:
                fp.write(page.content())
        except Exception:
            pass

        # 產出候選樣本，讓我們不用開 F12 也能精準調整 selector
        _dump_samples(
            page,
            selectors=[
                "a[data-article-id]",
                "a[href*='/tw/v3/article/']",
                "a[href*='/article/']",
                "[role='article'] a[href]",
                "article a[href*='/detail/']",
                "section a[href*='/detail/']",
            ],
            out_html="data/debug/linetoday_items_sample.html",
        )

        items = _extract(page, source_cfg)
        context.close()
        browser.close()

    df = pd.DataFrame(items)
    for col in ["source", "id", "title", "url", "author", "category", "date", "price"]:
        if col not in df.columns:
            df[col] = ""
    df["source"] = source_cfg.get("name", df.get("source", ""))
    return df
