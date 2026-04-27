import os
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from site_url import resolve_site_url


class SiteUrlTests(unittest.TestCase):
    def test_resolve_site_url_uses_explicit_site_url_first(self) -> None:
        os.environ["SITE_URL"] = "https://example.com/digest/"
        os.environ["GITHUB_REPOSITORY"] = "LarryinMexico/daily-news"
        self.assertEqual(resolve_site_url(), "https://example.com/digest/")

    def test_resolve_site_url_derives_github_pages_url(self) -> None:
        os.environ.pop("SITE_URL", None)
        os.environ["GITHUB_REPOSITORY"] = "LarryinMexico/daily-news"
        self.assertEqual(
            resolve_site_url(),
            "https://larryinmexico.github.io/daily-news/",
        )


if __name__ == "__main__":
    unittest.main()
