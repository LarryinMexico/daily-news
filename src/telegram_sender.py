from __future__ import annotations

import re
from typing import List

import requests


TELEGRAM_API_BASE = "https://api.telegram.org"
TELEGRAM_MESSAGE_LIMIT = 4096
MARKDOWN_V2_SPECIAL_CHARS = r"_*[]()~`>#+-=|{}.!"


def escape_markdown_v2(text: str) -> str:
    escaped = text or ""
    for char in MARKDOWN_V2_SPECIAL_CHARS:
        escaped = escaped.replace(char, f"\\{char}")
    return escaped


def unescape_markdown_v2(text: str) -> str:
    pattern = r"\\([_\*\[\]\(\)~`>#+\-=|{}.!])"
    return re.sub(pattern, r"\1", text or "")


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT - 150) -> List[str]:
    if len(text) <= limit:
        return [text]

    chunks: List[str] = []
    current = ""
    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue

        if current:
            chunks.append(current)
            current = ""

        if len(paragraph) <= limit:
            current = paragraph
            continue

        start = 0
        while start < len(paragraph):
            chunks.append(paragraph[start : start + limit])
            start += limit

    if current:
        chunks.append(current)
    return chunks


def send_markdown_messages(bot_token: str, chat_id: str, text: str) -> None:
    if not bot_token or not chat_id or not text:
        return

    for chunk in split_message(text):
        markdown_response = requests.post(
            f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "MarkdownV2",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        try:
            markdown_response.raise_for_status()
        except requests.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code != 400:
                raise

            plain_response = requests.post(
                f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": unescape_markdown_v2(chunk),
                    "disable_web_page_preview": True,
                },
                timeout=20,
            )
            plain_response.raise_for_status()
