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

### 1. 建立環境
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install   # 第一次安裝瀏覽器
```

### 2. 第一次執行（建立初始快照）
```bash
bash run_first_time.sh
```

### 3. 第二次（或後續）執行（產生差異報告）
```bash
bash run_incremental.sh
```

### 4. 查看 CLI 幫助
```bash
python -m interface.cli --help
```

### 5. 啟動 Streamlit 介面（可選）
```bash
streamlit run src/interface/app.py
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
├─ tests/                 # pytest 測試
├─ run_first_time.sh      # 初次執行腳本
├─ run_incremental.sh     # 增量更新腳本
├─ requirements.txt
├─ pyproject.toml
└─ README.md
```

---

## 作業交付檢查清單
- [x] 程式碼 + README  
- [x] 初次與後續快照（CSV）  
- [x] `diff_YYYYMMDD.csv` + `summary.json`  
- [x] 3–5 張 PNG 圖表（由 `pipeline/diff.py` 產生）  
- [x] 6–10 頁技術報告（請放到 `report/` 目錄下，自行撰寫）  

---

## 注意事項
- **robots.txt**：會自動檢查，不允許的網址不會爬。  
- **退避策略**：遇到 429/5xx 會自動延遲後重試。  
- **資料正規化**：日期統一轉為 `YYYYMMDD`，價格轉數值。  
- **唯一鍵**：以 `(source, id)` 作為主鍵。  
- **last_seen_at**：每次更新會記錄 UTC 時間。
