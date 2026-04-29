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

## JSON 輸出

每次執行會產生：

- `docs/data/tw_YYYYMMDD.json`
- `docs/data/us_YYYYMMDD.json`
- `docs/data/index.json`
