from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "docs" / "data"
INDEX_FILE = DATA_DIR / "index.json"


def build_index_payload() -> dict | None:
    if not DATA_DIR.exists():
        return None

    dates = set()
    latest_tw = None
    latest_us = None

    for path in DATA_DIR.glob("*.json"):
        if path.name == "index.json":
            continue

        stem = path.stem
        if stem.startswith("tw_"):
            date = stem.replace("tw_", "", 1)
            dates.add(date)
            latest_tw = max(filter(None, [latest_tw, date]))
        elif stem.startswith("us_"):
            date = stem.replace("us_", "", 1)
            dates.add(date)
            latest_us = max(filter(None, [latest_us, date]))

    if not dates:
        return None

    return {
        "available_dates": sorted(dates),
        "latest_tw": latest_tw,
        "latest_us": latest_us,
    }


def main() -> None:
    payload = build_index_payload()
    if payload is None:
        return

    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
