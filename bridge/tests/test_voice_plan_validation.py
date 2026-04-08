import unittest

from pydantic import ValidationError

from bridge.server import VoicePlanRequest


class VoicePlanValidationTests(unittest.TestCase):
    def test_empty_whitespace_text_fails_validation(self) -> None:
        with self.assertRaises(ValidationError):
            VoicePlanRequest(text="   ")

    def test_non_empty_text_passes_validation(self) -> None:
        req = VoicePlanRequest(text=" 山风江月 ")
        self.assertEqual(req.text, "山风江月")


if __name__ == "__main__":
    unittest.main()
