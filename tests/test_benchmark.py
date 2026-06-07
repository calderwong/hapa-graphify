from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hapa_graphify.benchmark import run_benchmark


class BenchmarkTests(unittest.TestCase):
    def test_run_benchmark_shape_and_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "perf.json"
            result = run_benchmark(output=output, limit_per_source=5)
            self.assertTrue(result["ok"], result)
            self.assertTrue(output.exists())
            self.assertGreater(result["baseline"]["node_count"], 0)
            self.assertIn("ui_strategy", result)
            self.assertEqual(result["baseline"]["mcp_guard_error"], "graph_too_large")


if __name__ == "__main__":
    unittest.main()
