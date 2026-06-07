from __future__ import annotations

import unittest
from datetime import date

from hapa_graphify.narrative import Period
from hapa_graphify.narrative_enrichment import (
    _candidate_terms,
    _entry_period,
    _merge_entry_enrichment,
    _overall_context,
)


class NarrativeEnrichmentTests(unittest.TestCase):
    def test_entry_period_from_weekly_entry(self) -> None:
        entry = {
            "kind": "weekly",
            "period": {"start": "2026-01-01", "end": "2026-01-07"},
        }
        self.assertEqual(_entry_period(entry), Period("weekly", date(2026, 1, 1), date(2026, 1, 7)))

    def test_candidate_terms_use_entry_and_overall_context(self) -> None:
        entry = {
            "id": "week-1",
            "title": "Week of 2026-01-01: Protocol / Graph",
            "evidence": {
                "top_topics": [{"key": "knowledge systems", "count": 3}],
                "top_keywords": [{"key": "Graphify", "count": 2}],
            },
        }
        payload = {
            "entries": [
                entry,
                {
                    "id": "week-2",
                    "evidence": {"top_topics": [{"key": "knowledge systems", "count": 5}], "top_keywords": []},
                },
            ]
        }
        packet = {"keyword_counts": [{"key": "protocol", "count": 4}]}
        terms = _candidate_terms(entry, packet, _overall_context(payload), {"previous": None, "next": payload["entries"][1]})
        self.assertIn("Graphify", terms)
        self.assertIn("protocol", terms)
        self.assertIn("knowledge systems", terms)
        self.assertIn("Hapa Protocol", terms)

    def test_merge_entry_enrichment_keeps_pass_history(self) -> None:
        entry = {
            "enrichment": {
                "passes": [{"pass_id": "old", "agent_id": "agent-a"}],
            }
        }
        bundle = {
            "summary": "new",
            "passes": [{"pass_id": "new", "agent_id": "agent-b"}],
        }
        _merge_entry_enrichment(entry, bundle)
        self.assertEqual(entry["enrichment"]["summary"], "new")
        self.assertEqual([item["pass_id"] for item in entry["enrichment"]["passes"]], ["old", "new"])
        self.assertEqual(entry["enrichment"]["pass_count"], 2)


if __name__ == "__main__":
    unittest.main()
