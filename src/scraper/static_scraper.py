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
    if not node: return ""
    return node.get(attr, "") if attr else extract_text(node)

def scrape_static(source_cfg: dict) -> pd.DataFrame:
    url = source_cfg["list_url"]
    if not allowed_by_robots(url):
        raise RuntimeError(f"Blocked by robots.txt: {url}")
    resp = requests.get(url, timeout=20)
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
                val = urljoin(url, val)
            row[field] = val
        row["source"] = source_cfg["name"]
        rows.append(row)
    return pd.DataFrame(rows)
