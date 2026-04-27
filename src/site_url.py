from __future__ import annotations

import os


def resolve_site_url() -> str:
    explicit_url = os.getenv("SITE_URL", "").strip()
    if explicit_url:
        return explicit_url

    repository = os.getenv("GITHUB_REPOSITORY", "").strip()
    if not repository or "/" not in repository:
        return ""

    owner, repo = repository.split("/", 1)
    return f"https://{owner.lower()}.github.io/{repo}/"
