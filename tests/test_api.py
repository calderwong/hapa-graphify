from __future__ import annotations

import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer

from hapa_graphify.api import HapaGraphifyHandler, route_request


class ApiTests(unittest.TestCase):
    def test_route_health(self) -> None:
        result = route_request("GET", "/health", {"deep": ["1"]})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["node_id"], "hapa-graphify")

    def test_route_append_dry_run(self) -> None:
        result = route_request("GET", "/api/append", {"dry_run": ["1"]})
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["dry_run"])

    def test_route_ecosystem_discover(self) -> None:
        result = route_request("GET", "/api/ecosystem/discover", {})
        self.assertTrue(result["ok"], result)
        self.assertGreaterEqual(result["node_root_count"], 1)
        self.assertIn("codebases", result)

    def test_route_knowledge_graph_sample(self) -> None:
        result = route_request(
            "GET",
            "/api/knowledge/graph",
            {
                "limit_per_source": ["2"],
                "source": ["second-brain-live", "hapa-front-door-docs"],
            },
        )
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["source_ids"], ["second-brain-live", "hapa-front-door-docs"])
        self.assertGreater(result["graph"]["node_count"], 0)

    def test_route_reports(self) -> None:
        result = route_request("GET", "/api/reports", {})
        self.assertTrue(result["ok"], result)
        self.assertIn("summaries", result)
        self.assertIn("reports_dir", result)

    def test_route_map(self) -> None:
        result = route_request("GET", "/api/map", {"kind": ["knowledge"], "level": ["type"], "limit": ["8"]})
        self.assertTrue(result["ok"], result)
        self.assertIn("nodes", result)
        self.assertIn("edges", result)

    def test_route_map_defaults_to_all(self) -> None:
        result = route_request("GET", "/api/map", {"level": ["source_type"], "limit": ["8"]})
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["kind"], "all")
        self.assertIn("nodes", result)

    def test_route_map_neighbors(self) -> None:
        overview = route_request("GET", "/api/map", {"kind": ["knowledge"], "level": ["source_type"], "limit": ["8"]})
        self.assertTrue(overview["ok"], overview)
        if not overview["nodes"]:
            self.skipTest("map sidecars not available")
        result = route_request(
            "GET",
            "/api/map/neighbors",
            {
                "kind": ["knowledge"],
                "level": ["source_type"],
                "id": [overview["nodes"][0]["id"]],
                "limit": ["8"],
            },
        )
        self.assertTrue(result["ok"], result)
        self.assertGreaterEqual(len(result["nodes"]), 1)
        self.assertEqual(result["focus"]["id"], overview["nodes"][0]["id"])

    def test_route_browse_sample(self) -> None:
        result = route_request(
            "GET",
            "/api/browse",
            {
                "source": ["hapa-front-door-docs"],
                "limit": ["5"],
                "limit_per_source": ["5"],
            },
        )
        self.assertTrue(result["ok"], result)
        self.assertLessEqual(len(result["nodes"]), 5)
        self.assertGreater(result["graph"]["node_count"], 0)

    def test_loopback_server_health_and_checkpoint_dry_run(self) -> None:
        server = ThreadingHTTPServer(("127.0.0.1", 0), HapaGraphifyHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urllib.request.urlopen(f"{base}/health", timeout=2) as response:
                health = json.loads(response.read().decode("utf-8"))
            self.assertTrue(health["ok"], health)

            with urllib.request.urlopen(f"{base}/ui", timeout=2) as response:
                html = response.read().decode("utf-8")
            self.assertIn("Hapa Graphify Operator", html)

            request = urllib.request.Request(
                f"{base}/api/board/checkpoint",
                data=json.dumps({"message": "test checkpoint", "dry_run": True}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=2) as response:
                checkpoint = json.loads(response.read().decode("utf-8"))
            self.assertTrue(checkpoint["ok"], checkpoint)
            self.assertTrue(checkpoint["dry_run"])
            self.assertTrue(checkpoint["would_append"])
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
