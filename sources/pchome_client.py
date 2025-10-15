import time
import json
import random
import requests
from typing import List, Dict, Any, Iterable

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript,*/*;q=0.1",
    "Referer": "https://24h.pchome.com.tw/",
    "Origin": "https://24h.pchome.com.tw",
    "Connection": "keep-alive",
}

def _chunk(it: List[str], size: int):
    for i in range(0, len(it), size):
        yield it[i:i+size]

class PChomeClient:
    """
    - search_page(): 關鍵字搜尋（內建多端點 fallback）
    - prod_status(): 銷售/上架狀態（JSON）
    - prod_specs(): 規格資訊（JSONP 去殼）
    具備 429/5xx 的指數退避與 jitter。
    """
    def __init__(self, timeout=15, max_retries=5, backoff=(0.8, 2.0)):
        self.s = requests.Session()
        self.s.headers.update(DEFAULT_HEADERS)
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff = backoff  # (base_delay, factor)

    def _request_once(self, url: str, to_json: bool = True):
        r = self.s.get(url, timeout=self.timeout)
        if r.status_code == 200:
            return r.json() if to_json else r.text
        # 回傳 404/403/5xx 交由上層處理（換端點或重試）
        raise requests.HTTPError(f"{r.status_code} for {url}", response=r)

    def _get(self, url: str, to_json: bool = True):
        delay = self.backoff[0]
        for _ in range(self.max_retries):
            try:
                return self._request_once(url, to_json=to_json)
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status in (429, 500, 502, 503, 504):
                    time.sleep(delay + random.uniform(0, 0.5))
                    delay *= self.backoff[1]
                    continue
                # 404/403 直接丟回去給上層換端點
                raise
        raise RuntimeError(f"Request failed after retries: {url}")

    def search_page(self, q: str, page: int = 1, sort: str = "rnk/dc") -> Dict[str, Any]:
        """
        嘗試多個常見端點；PChome 會改版，這裡逐一 fallback。
        只要打到其中一個可用，就回傳 JSON。
        """
        from urllib.parse import quote
        q_enc = quote(q)

        candidates = [
            # 常見舊版
            f"https://ecapi.pchome.com.tw/search/v3.3/all/results?q={q_enc}&page={page}&sort={sort}",
            f"https://ecapi.pchome.com.tw/search/v3.0/all/results?q={q_enc}&page={page}&sort={sort}",
            # site/24h 變體
            f"https://ecapi.pchome.com.tw/search/v3.3/24h/results?q={q_enc}&page={page}&sort={sort}",
            # 少帶 sort 的容錯
            f"https://ecapi.pchome.com.tw/search/v3.3/all/results?q={q_enc}&page={page}",
            # CDN 變體
            f"https://ecapi-cdn.pchome.com.tw/search/v3.3/all/results?q={q_enc}&page={page}&sort={sort}",
            # 邊緣搜尋（不同 JSON 結構，下面 fetch 端已有多鍵名容錯）
            f"https://ecapi-cdn.pchome.com.tw/fsapi/edge-search/v1.3/search?q={q_enc}&page={page}",
        ]

        last_err = None
        for url in candidates:
            try:
                return self._get(url, to_json=True)
            except Exception as e:
                last_err = e
                continue
        # 全部失敗時，給出可診斷訊息
        raise RuntimeError(
            "All search endpoints failed. Open Chrome DevTools on 24h.pchome.com.tw "
            "Search page → Network → XHR，複製實際的 JSON 請求 URL 後貼到程式內。"
        ) from last_err

    def prod_status(self, ids: List[str]) -> Dict[str, Any]:
        res = {}
        for batch in _chunk(ids, 20):
            url = "https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/button&id=" + ",".join(batch)
            part = self._get(url, to_json=True)
            if isinstance(part, dict):
                res.update(part)
        return res

    def prod_specs(self, ids: List[str]) -> Dict[str, Any]:
        res = {}
        for batch in _chunk(ids, 20):
            url = (
                "https://ecapi.pchome.com.tw/ecshop/prodapi/v2/prod/spec"
                + "?id=" + ",".join(batch)
                + "&_callback=jsonpcb_spec"
            )
            txt = self._get(url, to_json=False)
            start = txt.find("(") + 1
            end = txt.rfind(")")
            core = txt[start:end] if 0 < start < end else "{}"
            part = json.loads(core)
            if isinstance(part, dict):
                res.update(part)
        return res
