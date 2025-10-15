# 雙來源網頁爬蟲（靜態 + 動態）增量更新與差異比較  

課程：資訊檢索與生成式人工智慧 – 期中專案 I  
繳交日期：2025/10/15  

本專案實作內容：  
- 從 **兩個來源** 擷取資料（1 個靜態 HTML 使用 `requests+BeautifulSoup`，1 個動態網頁使用 **Playwright**）。  
- 將資料儲存成結構化格式（CSV 快照）。  
- **支援增量更新**：比較新舊兩次快照，輸出新增 / 刪除 / 修改的資料，並寫出 `diff_YYYYMMDD.csv` 與 `summary.json`。  
- 提供最小化介面：**命令列（CLI）** + **Streamlit 簡易頁面**（含 1 張圖表）。  
- 具備錯誤處理：重試 / backoff、尊重 robots.txt。  
- 可重現性：提供 `run_first_time.sh` / `run_incremental.sh` 腳本。  
- 測試（pytest）：檢查 selectors、去重、欄位驗證、diff 功能。  

> **注意**：請先在 `config/sources.yaml` 填入實際要爬的網站與選擇器，確保每個來源至少 100 筆資料。  

---

## 快速開始

### 1. 取得專案
```bash
git clone https://github.com/<你的帳號>/webscraper.git
cd webscraper

```

### 2. 建立與啟用虛擬環境
```bash
py -3.12 -m venv .venv
. .\.venv\Scripts\Activate.ps1
python -V   # 應顯示 3.12.x
```

### 3. 安裝依賴與瀏覽器
```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
python -m pip install playwright requests beautifulsoup4 lxml pandas matplotlib streamlit
python -m playwright install
# Linux 可能還需要：python -m playwright install-deps
```

### 4. 第一次執行（產生快照）
```bash
python -m src.interface.cli scrape --config config/sources.yaml --out data/snapshots
python -m src.interface.cli clean  --snapshots data/snapshots
```

### 5. 第二次執行（再抓一次 → 做差異）
```bash
python -m src.interface.cli scrape --config config/sources.yaml --out data/snapshots
python -m src.interface.cli clean  --snapshots data/snapshots
python -m src.interface.cli diff   --snapshots data/snapshots --diffs data/diffs --charts data/charts
# diff 比對差異產生圖，差異數據放在 data/diffs，圖放在 data/charts
```
<img width="427" height="187" alt="image" src="https://github.com/user-attachments/assets/7a85539f-3450-4e2d-9295-5e3ea8bcf7b9" />

### 6. 視覺化網頁
```bash
python -m streamlit run app.py
# 若是沒要跳出網頁，而是終端機出現 email ，點 enter 後，終端機才會繼續往下跑
```

### 7. 快速驗證（別盲信自己跑對了）
```bash
python -c "import pandas as pd, pathlib; p=sorted(pathlib.Path('data/snapshots').glob('snapshot_*.csv'))[-1]; df=pd.read_csv(p); print('rows=',len(df)); print(df['source'].value_counts().to_dict())"
# 期望接近：{'books_static': 200, 'quotes_dynamic_js': 100}
```
### 8. 想在 demo 製造可解釋的差異？
```bash
第一次把 config/sources.yaml 的 max_pages 設小（如 books=3 / quotes=5），第二次改大（10/10）→ new > 0

反過來（先大後小）→ deleted > 0
```
### 9. Pytest 單元測試
```bash
本專案使用 **pytest** 框架進行單元測試，確保各模組功能的正確性與穩定性。

1.
####  test_selectors.py
驗證設定檔的載入與結構完整性。

- ✅ 測試 `config/sources.yaml` 能否正確讀取
- ✅ 驗證設定檔包含 2 個資料來源
- ✅ 檢查必要欄位：`name`、`type`、`list_url`、`item_selector`

2.
####  test_validation.py
測試資料清理與格式化函式。

**日期標準化測試**
- 將 `2024-01-02` 轉換為 `20240102`
- 處理已格式化的日期
- 處理無效日期返回空字串

**數字轉換測試**
- 解析 `$1,234.56` 轉為 `1234.56`
- 處理 `N/A` 返回 `None`
- 正確處理負數值

3.
####  test_dedup.py
驗證去重邏輯的正確性。

- 建立包含重複資料的測試 DataFrame（相同 `source` + `id`）
- 驗證 `clean_df()` 能正確移除重複項目
- 確認自動產生 `pk`（primary key）欄位

4.
####  test_diff.py
測試快照比對功能。

- 建立兩個 CSV 快照檔案（前一次 vs 當前）
- 驗證 `diff_snapshots()` 能正確識別：
  - **新增項目**（new）
  - **刪除項目**（deleted）
  - **變更項目**（changed）

### 執行測試
執行所有測試
pytest tests/

執行特定測試檔案
pytest tests/test_validation.py

顯示詳細輸出
pytest -v

顯示測試覆蓋率報告
pytest --cov=src tests/
```

### 常見雷區（90% 卡在這）
```bash
ModuleNotFoundError: interface → 用我們的入口：python -m src.interface.cli（或先設 PYTHONPATH=src）。

Playwright 沒裝瀏覽器 → 跑 python -m playwright install；Linux 再加 python -m playwright install-deps。

PowerShell 跑不動 .ps1 → Set-ExecutionPolicy -Scope Process RemoteSigned（當前視窗有效）。

安裝科學套件失敗 → 你不是 3.12？請檢查 python -V；我們已鎖 matplotlib==3.8.4 以用預編譯 wheel。
```
---

## 專案結構
```
dual-source-webscraper/
├─ config/
│  └─ sources.yaml        # 來源設定檔
├─ data/
│  ├─ snapshots/          # 快照檔案
│  ├─ diffs/              # 差異檔案與 summary.json
│  ├─ charts/             # 圖表 PNG
│  └─ logs/               # 爬蟲錯誤紀錄
├─ src/
│  ├─ scraper/            # 靜態與動態爬蟲
│  ├─ pipeline/           # 清理、儲存、diff 處理
│  └─ interface/          # CLI 與 Streamlit 介面
|
├─ tests/                 # pytest 測試
│  ├─ test_dedup/         # 測試去重功能
│  ├─ test_diff/          # 測試快照比對功能
│  ├─ test_selectors/     # 驗證設定檔載入與格式正確性
│  └─ test_validation/    # 測試資料清理與格式化函式
├─ run_first_time.sh      # 初次執行腳本
├─ run_incremental.sh     # 增量更新腳本
├─ app.py                 # 以網頁顯示視覺化結果
├─ requirements.txt
├─ pyproject.toml
└─ README.md
```

---

## 作業交付檢查清單
- [V] 程式碼 + README  
- [V] 初次與後續快照（CSV）  
- [V] `diff_YYYYMMDD.csv` + `summary.json`  
- [x] 3–5 張 PNG 圖表（由 `pipeline/diff.py` 產生）  
- [x] 6–10 頁技術報告（請放到 `report/` 目錄下，自行撰寫）  

---

## 注意事項
- **robots.txt**：會自動檢查，不允許的網址不會爬。  
- **退避策略**：遇到 429/5xx 會自動延遲後重試。  
- **資料正規化**：日期統一轉為 `YYYYMMDD`，價格轉數值。  
- **唯一鍵**：以 `(source, id)` 作為主鍵。  
- **last_seen_at**：每次更新會記錄 UTC 時間。
