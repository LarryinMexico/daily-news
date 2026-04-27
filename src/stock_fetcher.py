from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import yfinance as yf


def load_watchlist(path: Path) -> Dict[str, List[Dict[str, str]]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _round_number(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), 2)


def _empty_snapshot(symbol: str, name: Optional[str] = None) -> Dict[str, Optional[float]]:
    return {
        "symbol": symbol,
        "name": name or symbol,
        "price": None,
        "change": None,
        "change_pct": None,
    }


def fetch_symbol_snapshot(symbol: str, *, name: Optional[str] = None) -> Dict[str, Optional[float]]:
    try:
        history = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=False)
        if history.empty:
            return _empty_snapshot(symbol, name)

        closes = history["Close"].dropna()
        if closes.empty:
            return _empty_snapshot(symbol, name)

        latest_price = float(closes.iloc[-1])
        previous_price = float(closes.iloc[-2]) if len(closes) > 1 else latest_price
        change = latest_price - previous_price
        change_pct = (change / previous_price * 100) if previous_price else 0.0

        return {
            "symbol": symbol,
            "name": name or symbol,
            "price": _round_number(latest_price),
            "change": _round_number(change),
            "change_pct": _round_number(change_pct),
        }
    except Exception:
        return _empty_snapshot(symbol, name)


def fetch_watchlist_quotes(watchlist: Iterable[Dict[str, str]]) -> List[Dict[str, Optional[float]]]:
    return [
        fetch_symbol_snapshot(item["symbol"], name=item.get("name"))
        for item in watchlist
    ]


def fetch_market_map(mapping: Dict[str, Dict[str, str]]) -> Dict[str, Dict[str, Optional[float]]]:
    results: Dict[str, Dict[str, Optional[float]]] = {}
    for key, meta in mapping.items():
        snapshot = fetch_symbol_snapshot(meta["symbol"], name=meta.get("name"))
        results[key] = {
            "price": snapshot.get("price"),
            "change_pct": snapshot.get("change_pct"),
        }
    return results
