from __future__ import annotations

import html
import re
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import feedparser
import requests


DEFAULT_TIMEOUT = 20
TRUTH_SOCIAL_RSS_URL = "https://truthsocial.com/@realDonaldTrump.rss"


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = html.unescape(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _normalize_article(
    title: str,
    summary: str,
    source: str,
    url: str = "",
    published_at: str = "",
) -> Dict[str, str]:
    return {
        "title": _clean_text(title) or "未提供標題",
        "summary": _clean_text(summary) or "⚠️ 資料暫時無法取得",
        "source": source or "Unknown",
        "url": url or "",
        "published_at": published_at or "",
    }


def _fallback_article(source: str) -> List[Dict[str, str]]:
    return [
        _normalize_article(
            title="⚠️ 資料暫時無法取得",
            summary="來源暫時無回應，系統已略過該來源並繼續執行。",
            source=source,
        )
    ]


def fetch_newsapi_articles(
    api_key: str,
    query: str,
    *,
    page_size: int = 10,
    language: str = "en",
    sort_by: str = "publishedAt",
) -> List[Dict[str, str]]:
    if not api_key:
        return _fallback_article("NewsAPI")

    try:
        response = requests.get(
            "https://newsapi.org/v2/everything",
            params={
                "q": query,
                "apiKey": api_key,
                "pageSize": page_size,
                "language": language,
                "sortBy": sort_by,
            },
            timeout=DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        articles = payload.get("articles", [])
        if not articles:
            return _fallback_article("NewsAPI")

        return [
            _normalize_article(
                title=article.get("title", ""),
                summary=article.get("description", "") or article.get("content", ""),
                source=(article.get("source") or {}).get("name", "NewsAPI"),
                url=article.get("url", ""),
                published_at=article.get("publishedAt", ""),
            )
            for article in articles[:page_size]
        ]
    except Exception:
        return _fallback_article("NewsAPI")


def fetch_rss_feed(
    url: str,
    *,
    source_name: str,
    limit: int = 10,
) -> List[Dict[str, str]]:
    try:
        feed = feedparser.parse(url)
        if getattr(feed, "bozo", 0) and not getattr(feed, "entries", []):
            return _fallback_article(source_name)

        entries = []
        for entry in getattr(feed, "entries", [])[:limit]:
            entries.append(
                _normalize_article(
                    title=entry.get("title", ""),
                    summary=entry.get("summary", "") or entry.get("description", ""),
                    source=source_name,
                    url=entry.get("link", ""),
                    published_at=entry.get("published", "") or entry.get("updated", ""),
                )
            )

        return entries or _fallback_article(source_name)
    except Exception:
        return _fallback_article(source_name)


def fetch_google_news_search(
    query: str,
    *,
    limit: int = 10,
    hl: str = "en-US",
    gl: str = "US",
    ceid: str = "US:en",
) -> List[Dict[str, str]]:
    encoded_query = quote_plus(query)
    url = (
        "https://news.google.com/rss/search"
        f"?q={encoded_query}&hl={hl}&gl={gl}&ceid={ceid}"
    )
    return fetch_rss_feed(url, source_name="Google News", limit=limit)


def fetch_truth_social_updates(limit: int = 5) -> List[Dict[str, str]]:
    return fetch_rss_feed(TRUTH_SOCIAL_RSS_URL, source_name="Truth Social", limit=limit)


def dedupe_articles(items: List[Dict[str, str]], *, max_items: int = 10) -> List[Dict[str, str]]:
    real_items = [
        item for item in items if not item.get("title", "").startswith("⚠️")
    ]
    source_items = real_items or items

    seen = set()
    deduped: List[Dict[str, str]] = []
    for item in source_items:
        key = (item.get("title", "").strip().lower(), item.get("url", "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break
    return deduped
