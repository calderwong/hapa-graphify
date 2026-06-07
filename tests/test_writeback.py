from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hapa_graphify.writeback import plan_writeback


class WritebackTests(unittest.TestCase):
    def test_writeback_dry_run_rows_cite_run_id(self) -> None:
        plan = plan_writeback(dry_run=True, limit_per_source=5)
        self.assertTrue(plan["ok"], plan)
        self.assertTrue(plan["dry_run"])
        self.assertEqual(plan["private_path_leak_count"], 0)
        self.assertGreaterEqual(len(plan["second_brain_rows"]), 1)
        self.assertTrue(all(row["run_id"] == plan["run_id"] for row in plan["second_brain_rows"]))
        self.assertGreaterEqual(len(plan["lance_jsonl"]), 1)
        self.assertEqual(plan["lance_jsonl"][0]["metadata"]["run_id"], plan["run_id"])

    def test_writeback_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "writeback.json"
            plan = plan_writeback(dry_run=True, output=output, limit_per_source=5)
            self.assertTrue(plan["ok"], plan)
            self.assertTrue(output.exists())


if __name__ == "__main__":
    unittest.main()
