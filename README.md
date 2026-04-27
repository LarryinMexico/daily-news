# Daily News

一個完全無主機的「每日財經摘要」系統：由 GitHub Actions 定時執行 Python 腳本，抓取新聞與市場資料，呼叫 Gemini API 整理成摘要，透過 Telegram Bot 發送，同時把結構化 JSON 寫入 `docs/data/`，再由 GitHub Pages 直接提供前端閱讀頁面。

## 系統架構

文字版流程圖：

1. GitHub Actions 依排程或 `workflow_dispatch` 觸發。
2. `src/tw_digest.py` 或 `src/us_digest.py` 執行。
3. 腳本透過 `news_fetcher.py` 抓 NewsAPI、Google News RSS、Truth Social RSS。
4. 腳本透過 `stock_fetcher.py` 抓 Yahoo Finance 指數、自選股、期貨資料。
5. 腳本把原始材料送進 Gemini `gemini-1.5-flash` 生成結構化摘要。
6. 腳本呼叫 `telegram_sender.py` 將 Markdown 訊息分段送到 Telegram。
7. 腳本把當日摘要寫成 `docs/data/tw_YYYYMMDD.json` 或 `docs/data/us_YYYYMMDD.json`。
8. `src/generate_site.py` 掃描 `docs/data/` 並更新 `docs/data/index.json`。
9. GitHub Actions 自動 commit `docs/` 內容回 repo。
10. GitHub Pages 從 `/docs` 直接發布前端頁面，`docs/app.js` 動態讀取 JSON 顯示內容。

## Repo 結構

```text
daily-news/
├── .github/
│   └── workflows/
│       ├── tw_digest.yml
│       └── us_digest.yml
├── src/
│   ├── tw_digest.py
│   ├── us_digest.py
│   ├── news_fetcher.py
│   ├── stock_fetcher.py
│   ├── telegram_sender.py
│   └── generate_site.py
├── docs/
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── data/
│       ├── .gitkeep
│       └── index.json
├── config/
│   └── watchlist.json
├── requirements.txt
└── README.md
```

## 安裝與設定

### 1. Fork 或使用這個 repo

1. 到 GitHub 建立你自己的 repo，或直接 fork 這份 repo。
2. clone 到本機後可直接修改 `config/watchlist.json`、前端樣式或 workflow 排程。

### 2. 設定 GitHub Secrets

到 repo 的 `Settings → Secrets and variables → Actions`，新增以下 4 個 secrets：

1. `GEMINI_API_KEY`
2. `TELEGRAM_BOT_TOKEN`
3. `TELEGRAM_CHAT_ID`
4. `NEWS_API_KEY`

說明：

- `GEMINI_API_KEY`：用來呼叫 `gemini-1.5-flash`
- `TELEGRAM_BOT_TOKEN`：你的 Telegram Bot token
- `TELEGRAM_CHAT_ID`：接收訊息的 chat id
- `NEWS_API_KEY`：用來抓 NewsAPI 財經新聞

### 3. 開啟 GitHub Pages

到 `Settings → Pages`：

1. `Source` 選 `Deploy from a branch`
2. `Branch` 選 `main`
3. 資料夾選 `/docs`

完成後網址會是：

`https://{username}.github.io/{repo-name}/`

### 4. 手動測試 workflow

到 `Actions` 頁面：

1. 點 `台股每日早報`
2. 按 `Run workflow`
3. 再測一次 `美股每日早報`

第一次成功執行後，`docs/data/` 會出現摘要 JSON，前端頁面也會開始顯示內容。

## Workflow 排程

- `tw_digest.yml`：`0 0 * * 1-5`
- `us_digest.yml`：`30 13 * * 1-5`

這是 GitHub Actions 的 UTC cron。你可以依自己的時區需求調整。

## 如何修改自選股

編輯 `config/watchlist.json`。

範例：

```json
{
  "tw_stocks": [
    {"symbol": "2330.TW", "name": "台積電"}
  ],
  "us_stocks": [
    {"symbol": "NVDA", "name": "輝達"}
  ]
}
```

說明：

- 台股請使用 `.TW` 後綴，例如 `2330.TW`
- 美股直接用股票代號，例如 `AAPL`
- ETF 與指數也可以加入，只要 Yahoo Finance 找得到

## JSON 輸出

每次執行會產生：

- `docs/data/tw_YYYYMMDD.json`
- `docs/data/us_YYYYMMDD.json`
- `docs/data/index.json`

其中 `index.json` 提供前端日期切換器使用。

## 前端網址在哪裡找

啟用 GitHub Pages 後，網址通常是：

`https://{username}.github.io/{repo-name}/`

如果不確定：

1. 到 `Settings → Pages`
2. GitHub 會直接顯示 published site URL

## 本地開發

安裝依賴：

```bash
pip install -r requirements.txt
```

手動執行：

```bash
python src/tw_digest.py
python src/us_digest.py
python src/generate_site.py
```

## 錯誤處理設計

這個 repo 已內建以下保護：

- 每個新聞來源都有獨立 `try/except`
- NewsAPI、Google News RSS、Truth Social RSS 任一來源失敗時，不會中斷整體流程
- Yahoo Finance 單一標的抓取失敗時，其他標的仍會繼續
- Telegram 單則訊息超過 4096 字時會自動切段
- Gemini API 會 retry 最多 3 次，每次間隔 5 秒
- `generate_site.py` 在沒有任何摘要 JSON 時會直接結束，不報錯

## `economic_events` 的來源設計

美股摘要中的 `economic_events` 使用以下材料：

1. NewsAPI 的總經與聯準會關鍵字新聞
2. Google News RSS 的總經搜尋結果
3. Gemini 將上述內容整理成「今日重要經濟事件」

這代表它偏向「總經催化事件摘要」，不是交易所官方經濟日曆。

## 常見問題排查

### Actions 沒觸發

檢查：

1. repo 是否已推上 GitHub
2. workflow 檔案是否位於 `.github/workflows/`
3. branch 是否是 `main`
4. 是否為 private repo 且 Actions 配額或權限受限

可以先用 `workflow_dispatch` 手動執行確認。

### Telegram 沒收到

檢查：

1. `TELEGRAM_BOT_TOKEN` 是否正確
2. `TELEGRAM_CHAT_ID` 是否正確
3. Bot 是否已被加入對應 chat
4. 是否曾經先對 Bot 發過訊息，讓 Bot 有權限回覆

### 網頁沒更新

檢查：

1. workflow 是否成功跑完
2. commit/push `docs/` 的 step 是否成功
3. `Settings → Pages` 是否確實指到 `main /docs`
4. 瀏覽器是否快取舊版，先強制重新整理
5. `docs/data/index.json` 是否已有新日期

### NewsAPI 沒資料

檢查：

1. `NEWS_API_KEY` 是否有效
2. 是否超出免費額度
3. 關鍵字是否太窄，可改 `src/tw_digest.py` / `src/us_digest.py` 內的 query

### Gemini 失敗

檢查：

1. `GEMINI_API_KEY` 是否有效
2. 配額是否足夠
3. Actions log 中是否有連線或權限錯誤

如果 Gemini 失敗，系統仍會輸出 fallback JSON，但 AI 洞察內容會變成警示文字。

## GitHub Pages 設定提醒

GitHub Pages 不是自動開啟的，你需要手動到：

`Settings → Pages → Deploy from a branch → main → /docs`

設定完成後才會有公開網址。
