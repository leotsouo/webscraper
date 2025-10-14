# src/scraper/http_client.py

import requests
import time
from typing import Optional

RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 4
BASE_DELAY = 1.0  # 基礎延遲時間(秒)

def exponential_backoff(attempt: int, base_delay: float = BASE_DELAY) -> float:
    """
    計算指數退避延遲時間
    
    Args:
        attempt: 當前重試次數 (1-based)
        base_delay: 基礎延遲時間
    
    Returns:
        延遲秒數: base_delay * (2 ^ (attempt - 1))
        例如: 1s, 2s, 4s, 8s...
    """
    return base_delay * (2 ** (attempt - 1))

def get_with_retry(
    url: str, 
    session: Optional[requests.Session] = None,
    user_agent: Optional[str] = None,
    max_retries: int = MAX_RETRIES
) -> requests.Response:
    """
    帶重試機制的 HTTP GET 請求
    
    - 遇到 429 或 5xx 錯誤會自動重試
    - 使用指數退避策略
    - 尊重 Retry-After header
    
    Args:
        url: 目標 URL
        session: requests.Session 物件 (optional)
        user_agent: User-Agent header (optional)
        max_retries: 最大重試次數
    
    Returns:
        requests.Response 物件
        
    Raises:
        requests.RequestException: 超過最大重試次數後拋出
    """
    sess = session or requests.Session()
    
    if user_agent:
        sess.headers.update({"User-Agent": user_agent})
    
    last_exception = None
    
    for attempt in range(1, max_retries + 1):
        try:
            response = sess.get(url, timeout=30)
            
            # 如果狀態碼正常,直接回傳
            if response.status_code not in RETRY_STATUSES:
                return response
            
            # 處理需要重試的狀態碼
            if attempt < max_retries:
                # 優先檢查 Retry-After header
                retry_after = response.headers.get("Retry-After")
                
                if retry_after:
                    # Retry-After 可能是秒數或日期,這裡簡化處理為秒數
                    try:
                        wait_time = float(retry_after)
                    except ValueError:
                        wait_time = exponential_backoff(attempt)
                else:
                    wait_time = exponential_backoff(attempt)
                
                print(f"  HTTP {response.status_code} on {url}")
                print(f"   Retry {attempt}/{max_retries} after {wait_time:.1f}s...")
                time.sleep(wait_time)
                continue
            else:
                # 最後一次嘗試仍失敗
                response.raise_for_status()
                
        except requests.RequestException as e:
            last_exception = e
            
            if attempt < max_retries:
                wait_time = exponential_backoff(attempt)
                print(f"  Request failed: {e}")
                print(f"   Retry {attempt}/{max_retries} after {wait_time:.1f}s...")
                time.sleep(wait_time)
            else:
                print(f" Max retries exceeded for {url}")
                raise
    
    # 如果所有重試都失敗
    if last_exception:
        raise last_exception
    
    return response
