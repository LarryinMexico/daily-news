import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trump_curator import curate_trump_source_material


class TrumpCuratorTests(unittest.TestCase):
    def test_curate_trump_source_material_prefers_truth_social_and_filters_irrelevant_media(self) -> None:
        truth_items = [
            {
                "title": "Trump on Truth Social",
                "summary": "President Trump says tariff policy toward China will be reviewed this week.",
                "source": "Truth Social",
                "url": "https://truthsocial.com/post/1",
            }
        ]
        media_items = [
            {
                "title": "BBC - Trump says tariff policy could change on Taiwan chips",
                "summary": "Trump statement focused on tariff policy and semiconductor imports.",
                "source": "Google News",
                "url": "https://news.google.com/1",
            },
            {
                "title": "Salt Lake Tribune - Church members react to deportation rhetoric",
                "summary": "Reaction story about social controversy rather than a market policy announcement.",
                "source": "Google News",
                "url": "https://news.google.com/2",
            },
        ]

        curated = curate_trump_source_material(truth_items, media_items, max_items=3)

        self.assertEqual(len(curated), 2)
        self.assertEqual(curated[0]["source"], "Truth Social")
        self.assertIn("tariff policy", curated[1]["summary"].lower())
        self.assertNotIn("deportation rhetoric", " ".join(item["summary"] for item in curated).lower())


if __name__ == "__main__":
    unittest.main()
