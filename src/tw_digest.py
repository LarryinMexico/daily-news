from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from zoneinfo import ZoneInfo

from gemini_client import call_gemini_json
from news_fetcher import (
    dedupe_articles,
    fetch_google_news_search,
    fetch_newsapi_articles,
    fetch_rss_feed,
    fetch_truth_social_updates,
)
from site_url import resolve_site_url
from stock_fetcher import fetch_market_map, fetch_symbol_snapshot, fetch_watchlist_quotes, load_watchlist
from telegram_sender import escape_markdown_v2, send_markdown_messages


ROOT_DIR = Path(__file__).resolve().parents[1]
WATCHLIST_FILE = ROOT_DIR / "config" / "watchlist.json"
DATA_DIR = ROOT_DIR / "docs" / "data"

TAIPEI_TZ = ZoneInfo("Asia/Taipei")
UTC = timezone.utc


def utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def digest_date_strings() -> tuple[str, str]:
    now = datetime.now(TAIPEI_TZ)
    return now.strftime("%Y-%m-%d"), now.strftime("%Y%m%d")


def fallback_trump_updates() -> List[Dict[str, str]]:
    return [
        {
            "source": "Truth Social / Google News",
            "content": "⚠️ 資料暫時無法取得",
            "impact": "暫時無法完成川普政策動態分析。",
        }
    ]


def fallback_financial_news() -> List[Dict[str, str]]:
    return [
        {
            "title": "⚠️ 資料暫時無法取得",
            "summary": "本次整理時無法取得足夠新聞內容。",
            "impact": "請稍後重新執行或檢查 API 設定。",
        }
    ]


def count_real_articles(items: List[Dict[str, str]]) -> int:
    return sum(1 for item in items if not item.get("title", "").startswith("⚠️"))


def build_ai_sections(
    trump_articles: List[Dict[str, str]],
    financial_articles: List[Dict[str, str]],
    us_market_close: Dict[str, Dict[str, float | None]],
    tw_market_index: Dict[str, float | None],
    tw_watchlist: List[Dict[str, float | None]],
) -> Dict[str, Any]:
    prompt = f"""
You are a Taiwanese financial editor. Based only on the provided material, produce valid JSON in Traditional Chinese.

Return exactly this JSON schema:
{{
  "trump_updates": [
    {{
      "source": "string",
      "content": "string",
      "impact": "string"
    }}
  ],
  "financial_news": [
    {{
      "title": "string",
      "summary": "string",
      "impact": "string"
    }}
  ],
  "ai_insight": "string",
  "risks": ["string", "string"],
  "sentiment": "string"
}}

Rules:
- Keep all output in Traditional Chinese.
- Use 1 to 3 items for trump_updates.
- Use 3 to 5 items for financial_news.
- Base impact on Taiwanese equities and technology names when relevant.
- If the source material is thin, still return complete fields and be explicit about uncertainty.

US market close:
{json.dumps(us_market_close, ensure_ascii=False)}

Taiwan market index:
{json.dumps(tw_market_index, ensure_ascii=False)}

TW watchlist:
{json.dumps(tw_watchlist, ensure_ascii=False)}

Trump-related source material:
{json.dumps(trump_articles, ensure_ascii=False)}

Financial news source material:
{json.dumps(financial_articles, ensure_ascii=False)}
"""
    return call_gemini_json(prompt)


def safe_build_ai_sections(
    trump_articles: List[Dict[str, str]],
    financial_articles: List[Dict[str, str]],
    us_market_close: Dict[str, Dict[str, float | None]],
    tw_market_index: Dict[str, float | None],
    tw_watchlist: List[Dict[str, float | None]],
) -> Dict[str, Any]:
    try:
        result = build_ai_sections(
            trump_articles,
            financial_articles,
            us_market_close,
            tw_market_index,
            tw_watchlist,
        )
        return {
            "trump_updates": result.get("trump_updates") or fallback_trump_updates(),
            "financial_news": result.get("financial_news") or fallback_financial_news(),
            "ai_insight": result.get("ai_insight") or "⚠️ 本次 AI 洞察暫時無法生成。",
            "risks": result.get("risks") or ["⚠️ 風險整理暫時無法取得"],
            "sentiment": result.get("sentiment") or "市場情緒暫時無法判讀。",
        }
    except Exception as exc:
        print(f"[TW digest] AI summary failed: {exc}")
        return {
            "trump_updates": fallback_trump_updates(),
            "financial_news": fallback_financial_news(),
            "ai_insight": "⚠️ 本次 AI 洞察暫時無法生成。",
            "risks": ["⚠️ 風險整理暫時無法取得"],
            "sentiment": "市場情緒暫時無法判讀。",
        }


def build_message(payload: Dict[str, Any]) -> str:
    site_url = resolve_site_url()
    lines = [
        "*每日財經摘要｜台股早報*",
        f"日期：{escape_markdown_v2(payload['date'])}",
        "",
        "*美股收盤*",
    ]

    for label, key in [("S&P 500", "sp500"), ("Dow", "dow"), ("Nasdaq", "nasdaq")]:
        market = payload.get("us_market_close", {}).get(key, {})
        price = market.get("price")
        change_pct = market.get("change_pct")
        if price is None:
            lines.append(f"• {label}: ⚠️ 資料暫時無法取得")
        else:
            lines.append(
                f"• {label}: {escape_markdown_v2(str(price))} "
                f"({escape_markdown_v2(str(change_pct))}% )"
            )

    tw_index = payload.get("tw_market_index", {})
    lines.extend(
        [
            "",
            "*台股大盤*",
            "• "
            + (
                f"{escape_markdown_v2(tw_index.get('name', '加權指數'))}: "
                f"{escape_markdown_v2(str(tw_index.get('price')))} "
                f"({escape_markdown_v2(str(tw_index.get('change_pct')))}% )"
                if tw_index.get("price") is not None
                else "⚠️ 資料暫時無法取得"
            ),
            "",
            "*川普動態*",
        ]
    )

    for item in payload.get("trump_updates", []):
        lines.append(
            f"• {escape_markdown_v2(item.get('source', 'Unknown'))}: "
            f"{escape_markdown_v2(item.get('content', ''))}"
        )
        lines.append(f"  影響：{escape_markdown_v2(item.get('impact', ''))}")

    lines.extend(["", "*財經重點*", ""])
    for item in payload.get("financial_news", []):
        lines.append(f"• {escape_markdown_v2(item.get('title', ''))}")
        lines.append(f"  摘要：{escape_markdown_v2(item.get('summary', ''))}")
        lines.append(f"  影響：{escape_markdown_v2(item.get('impact', ''))}")

    lines.extend(["", "*AI 選股洞察*", escape_markdown_v2(payload.get("ai_insight", "")), "", "*風險提示*"])
    for risk in payload.get("risks", []):
        lines.append(f"• {escape_markdown_v2(risk)}")

    lines.extend(["", "*市場情緒*", escape_markdown_v2(payload.get("sentiment", ""))])
    if site_url:
        lines.extend(["", f"網頁版：{escape_markdown_v2(site_url)}"])
    return "\n".join(lines)


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    watchlist = load_watchlist(WATCHLIST_FILE)
    tw_watchlist = fetch_watchlist_quotes(watchlist.get("tw_stocks", []))
    tw_market_index = fetch_symbol_snapshot("^TWII", name="台灣加權指數")
    us_market_close = fetch_market_map(
        {
            "sp500": {"symbol": "^GSPC", "name": "S&P 500"},
            "dow": {"symbol": "^DJI", "name": "Dow Jones"},
            "nasdaq": {"symbol": "^IXIC", "name": "Nasdaq"},
        }
    )

    news_api_key = os.getenv("NEWS_API_KEY", "").strip()
    newsapi_items = fetch_newsapi_articles(
        news_api_key,
        "Taiwan stocks OR semiconductor OR Federal Reserve OR tariff OR inflation",
        page_size=6,
    )
    google_business_items = fetch_google_news_search(
        "Taiwan stock market semiconductor tariff fed inflation",
        limit=6,
    )
    google_macro_items = fetch_rss_feed(
        "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
        source_name="Google News Business",
        limit=6,
    )
    trump_truth_items = fetch_truth_social_updates(limit=3)
    trump_search_items = fetch_google_news_search("Trump statement policy", limit=3)

    print(f"[TW digest] NewsAPI articles: {count_real_articles(newsapi_items)}")
    print(f"[TW digest] Google market RSS articles: {count_real_articles(google_business_items)}")
    print(f"[TW digest] Google business topic RSS articles: {count_real_articles(google_macro_items)}")
    print(f"[TW digest] Truth Social items: {count_real_articles(trump_truth_items)}")
    print(f"[TW digest] Trump search RSS items: {count_real_articles(trump_search_items)}")

    financial_articles = dedupe_articles(
        newsapi_items + google_business_items + google_macro_items,
        max_items=8,
    )
    trump_articles = dedupe_articles(trump_truth_items + trump_search_items, max_items=4)

    print(f"[TW digest] Financial articles after dedupe: {len(financial_articles)}")
    print(f"[TW digest] Trump articles after dedupe: {len(trump_articles)}")

    ai_sections = safe_build_ai_sections(
        trump_articles,
        financial_articles,
        us_market_close,
        tw_market_index,
        tw_watchlist,
    )

    display_date, file_date = digest_date_strings()
    payload = {
        "date": display_date,
        "type": "tw",
        "generated_at": utc_timestamp(),
        "us_market_close": us_market_close,
        "tw_market_index": tw_market_index,
        "trump_updates": ai_sections["trump_updates"],
        "financial_news": ai_sections["financial_news"],
        "tw_watchlist": tw_watchlist,
        "ai_insight": ai_sections["ai_insight"],
        "risks": ai_sections["risks"],
        "sentiment": ai_sections["sentiment"],
    }

    output_file = DATA_DIR / f"tw_{file_date}.json"
    output_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    send_markdown_messages(bot_token, chat_id, build_message(payload))


if __name__ == "__main__":
    main()
