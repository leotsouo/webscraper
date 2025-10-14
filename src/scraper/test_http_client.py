# test_http_client.py (放在專案根目錄)

from http_client import get_with_retry, exponential_backoff

# 測試 1: 指數退避計算
print("=== 測試指數退避 ===")
for i in range(1, 5):
    delay = exponential_backoff(i)
    print(f"第 {i} 次重試延遲: {delay} 秒")

print("\n=== 測試 HTTP 請求 ===")
# 測試 2: 正常請求
try:
    response = get_with_retry("https://httpbin.org/status/200")
    print(f" 成功: 狀態碼 {response.status_code}")
except Exception as e:
    print(f" 失敗: {e}")

# 測試 3: 模擬 429 錯誤 (會自動重試)
try:
    response = get_with_retry("https://httpbin.org/status/429", max_retries=2)
    print(f"回應: {response.status_code}")
except Exception as e:
    print(f"預期的錯誤 (重試後仍失敗): {e}")
