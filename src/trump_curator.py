from __future__ import annotations

from typing import Dict, List


POLICY_INCLUDE_KEYWORDS = {
    "statement",
    "policy",
    "tariff",
    "trade",
    "china",
    "taiwan",
    "chip",
    "semiconductor",
    "economy",
    "economic",
    "export",
    "federal reserve",
    "inflation",
    "tax",
    "sanction",
    "market",
    "supply chain",
    "manufacturing",
    "energy",
    "immigration policy",
    "duty",
}

POLICY_EXCLUDE_KEYWORDS = {
    "church",
    "trial",
    "family",
    "wedding",
    "celebrity",
    "golf",
    "campaign rally",
    "endorsement",
    "podcast",
    "style",
    "fashion",
    "health secretary",
    "rfk",
    "kennedy",
    "silent",
    "regret",
}


def _is_truth_social(item: Dict[str, str]) -> bool:
    return (item.get("source") or "").strip().lower() == "truth social"


def _is_real_item(item: Dict[str, str]) -> bool:
    return not item.get("title", "").startswith("⚠️")


def _is_policy_relevant(item: Dict[str, str]) -> bool:
    haystack = " ".join(
        [
            item.get("title", ""),
            item.get("summary", ""),
            item.get("url", ""),
        ]
    ).lower()

    if any(keyword in haystack for keyword in POLICY_EXCLUDE_KEYWORDS):
        return False
    return any(keyword in haystack for keyword in POLICY_INCLUDE_KEYWORDS)


def _dedupe_articles(items: List[Dict[str, str]], *, max_items: int) -> List[Dict[str, str]]:
    seen = set()
    deduped: List[Dict[str, str]] = []
    for item in items:
        key = (item.get("title", "").strip().lower(), item.get("url", "").strip().lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= max_items:
            break
    return deduped


def curate_trump_source_material(
    truth_items: List[Dict[str, str]],
    media_items: List[Dict[str, str]],
    *,
    max_items: int = 4,
) -> List[Dict[str, str]]:
    prioritized_truth_items = [
        item for item in _dedupe_articles(truth_items, max_items=max_items) if _is_real_item(item)
    ]
    qualified_media_items = [
        item
        for item in _dedupe_articles(media_items, max_items=max_items * 2)
        if _is_real_item(item) and not _is_truth_social(item) and _is_policy_relevant(item)
    ]

    combined = prioritized_truth_items + qualified_media_items
    return _dedupe_articles(combined, max_items=max_items)
