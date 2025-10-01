import pandas as pd
from playwright.sync_api import sync_playwright
from .utils import allowed_by_robots, polite_delay
from urllib.parse import urljoin

def extract_attr(el, attr):
    try:
        return el.get_attribute(attr) or ""
    except Exception:
        return ""

def scrape_dynamic(source_cfg: dict) -> pd.DataFrame:
    url = source_cfg["list_url"]
    if not allowed_by_robots(url):
        raise RuntimeError(f"Blocked by robots.txt: {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        polite_delay()
        elements = page.query_selector_all(source_cfg["item_selector"])

        rows = []
        for el in elements:
            row = {}
            for field, selector in source_cfg["fields"].items():
                if not selector:
                    row[field] = ""
                    continue
                # attribute selector syntax: "<css> @ <attr>"
                if "@ " in selector or " @" in selector:
                    css, attr = selector.split("@")
                    node = page.query_selector(css.strip())
                    row[field] = extract_attr(node, attr.strip()) if node else ""
                else:
                    node = page.query_selector(selector)
                    row[field] = node.inner_text().strip() if node else ""
                if field == "url" and row[field]:
                    row[field] = urljoin(url, row[field])
            row["source"] = source_cfg["name"]
            rows.append(row)
        browser.close()
    return pd.DataFrame(rows)
