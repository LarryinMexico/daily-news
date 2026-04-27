import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gemini_client import call_gemini_json


class GeminiClientTests(unittest.TestCase):
    def test_call_gemini_json_uses_explicit_client_close(self) -> None:
        os.environ["GEMINI_API_KEY"] = "test-key"

        response = Mock()
        response.text = '{"sentiment": "neutral"}'

        client = Mock()
        client.models.generate_content.return_value = response

        fake_genai = Mock()
        fake_genai.Client.return_value = client
        fake_types = Mock()
        fake_types.GenerateContentConfig = Mock(return_value=object())

        with patch("gemini_client.load_genai_modules", return_value=(fake_genai, fake_types)):
            payload = call_gemini_json("Return JSON")

        self.assertEqual(payload, {"sentiment": "neutral"})
        fake_genai.Client.assert_called_once_with(api_key="test-key")
        client.models.generate_content.assert_called_once()
        client.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
