# src/scraper/error_handler.py
import os
import csv
import time
from datetime import datetime
from typing import Callable

from scraper.http_client import exponential_backoff, RobotsGuard


LOG_PATH = "data/logs/error_log.csv"

def log_error(url: str, error: str, attempt: int):
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(timespec="seconds"),
            url,
            attempt,
            error
        ])

def safe_delay_from_robots(url: str, fallback: float = 1.0):
    """
    根據 robots.txt 中的 crawl-delay 決定延遲，若沒有則使用 fallback。
    """
    guard = RobotsGuard()
    cd = guard.crawl_delay(url)
    if cd:
        time.sleep(cd)
    else:
        time.sleep(fallback)

def retry_with_backoff_for_playwright(max_retries: int = 4):
    """
    裝飾器：給 dynamic_scraper 的 page.goto() 用。
    自動處理 429 / 5xx / TimeoutError。
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    url = kwargs.get("url") or "N/A"
                    log_error(url, str(e), attempt)
                    delay = exponential_backoff(attempt)
                    time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
