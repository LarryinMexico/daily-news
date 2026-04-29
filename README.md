# Daily News

## 修改自選股

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

