import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from telegram_sender import send_markdown_messages


class TelegramSenderTests(unittest.TestCase):
    def test_send_markdown_messages_falls_back_to_plain_text_on_bad_markdown(self) -> None:
        bad_response = Mock()
        bad_response.status_code = 400
        bad_response.raise_for_status.side_effect = requests.HTTPError(response=bad_response)

        ok_response = Mock()
        ok_response.status_code = 200
        ok_response.raise_for_status.return_value = None

        with patch("telegram_sender.requests.post", side_effect=[bad_response, ok_response]) as mock_post:
            send_markdown_messages("token", "chat", "*標題*\nPrice \\(1\\)")

        first_payload = mock_post.call_args_list[0].kwargs["json"]
        second_payload = mock_post.call_args_list[1].kwargs["json"]

        self.assertEqual(first_payload["parse_mode"], "MarkdownV2")
        self.assertNotIn("parse_mode", second_payload)
        self.assertEqual(second_payload["text"], "*標題*\nPrice (1)")


if __name__ == "__main__":
    unittest.main()
