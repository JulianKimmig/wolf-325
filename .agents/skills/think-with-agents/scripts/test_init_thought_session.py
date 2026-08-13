#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

from init_thought_session import create_session, slugify_title


class ThoughtSessionTests(unittest.TestCase):
    def test_slugify_title_uses_safe_lowercase_slug(self):
        self.assertEqual(slugify_title("Map API: Auth & Billing!"), "map-api-auth-billing")

    def test_create_session_writes_expected_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            session = create_session(Path(tmp), "Map API Auth")

            self.assertEqual(session.name, "map-api-auth")
            self.assertTrue((session / "results").is_dir())
            for name in ("perspectives.md", "clarification.md", "summary.md"):
                content = (session / name).read_text(encoding="utf-8")
                self.assertIn("## Chain-of-Thought Summary", content)
                self.assertIn("## Running Log", content)

    def test_create_session_does_not_overwrite_existing_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = create_session(Path(tmp), "Map API Auth")
            second = create_session(Path(tmp), "Map API Auth", timestamp="20260603-120000")

            self.assertEqual(first.name, "map-api-auth")
            self.assertEqual(second.name, "map-api-auth-20260603-120000")


if __name__ == "__main__":
    unittest.main()
