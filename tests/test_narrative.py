from __future__ import annotations

import unittest
from datetime import date

from hapa_graphify.narrative import (
    Period,
    _redact_public_payload,
    _technical_paragraphs,
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


if __name__ == "__main__":
    unittest.main()
