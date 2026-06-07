from __future__ import annotations

import unittest
from datetime import date
from tempfile import TemporaryDirectory
from pathlib import Path

from hapa_graphify.narrative import (
    Period,
    _redact_public_payload,
    _technical_paragraphs,
    _write_png_illustration,
    _weekly_periods,
)


class NarrativeTests(unittest.TestCase):
    def test_weekly_periods_anchor_to_start_date(self) -> None:
        periods = _weekly_periods(date(2026, 1, 1), date(2026, 1, 15))
        self.assertEqual(len(periods), 3)
        self.assertEqual(periods[0], Period("weekly", date(2026, 1, 1), date(2026, 1, 7)))
        self.assertEqual(periods[-1], Period("weekly", date(2026, 1, 15), date(2026, 1, 15)))

    def test_redaction_removes_local_paths(self) -> None:
        payload = {
            "text": "See file:///Users/calderwong/Desktop/private.md and /Users/calderwong/.node_token",
            "items": ["calderwong", "safe"],
        }
        redacted = _redact_public_payload(payload)
        text = str(redacted)
        self.assertNotIn("/Users/calderwong", text)
        self.assertNotIn("file:///Users", text)
        self.assertNotIn("calderwong", text)
        self.assertIn("local-private-path", text)

    def test_empty_week_is_not_invented(self) -> None:
        period = Period("weekly", date(2026, 2, 5), date(2026, 2, 11))
        packet = {
            "evidence_counts": {"turns": 0, "wiki_articles": 0, "wiki_files": 0},
            "topic_counts": [],
            "turn_type_counts": [],
            "keyword_counts": [],
            "turns": [],
        }
        paragraphs = _technical_paragraphs(period, packet, None)
        self.assertEqual(len(paragraphs), 3)
        self.assertIn("no timestamped Second Brain turns", paragraphs[0])

    def test_png_illustration_is_optional_but_writes_when_available(self) -> None:
        try:
            import PIL  # noqa: F401
        except Exception:
            self.skipTest("Pillow is not installed")

        entry = {
            "id": "hapa-narrative-test",
            "title": "Week of 2026-01-01: Protocol / Graph",
            "period": {"label": "2026-01-01 to 2026-01-07"},
            "evidence": {
                "counts": {"turns": 12, "wiki_articles": 2, "wiki_files": 4},
                "top_topics": [{"key": "software engineering"}, {"key": "knowledge systems"}],
                "top_keywords": [{"key": "Graphify"}, {"key": "protocol"}],
            },
        }
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "card.png"
            self.assertTrue(_write_png_illustration(entry, output))
            self.assertGreater(output.stat().st_size, 1024)


if __name__ == "__main__":
    unittest.main()
