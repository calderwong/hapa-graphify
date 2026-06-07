from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hapa_graphify.core import (
    build_source_fragment,
    export_graph,
    is_credential_path,
    redact_public_fragment,
)


class SecurityPrivacyTests(unittest.TestCase):
    def test_credential_paths_are_blocked(self) -> None:
        blocked = [".env", ".node_token", "notes.db-wal", "notes.db-shm", "Raw/private.md", "Private/a.md", "tmp/a.txt"]
        for path in blocked:
            self.assertTrue(is_credential_path(path), path)
        self.assertFalse(is_credential_path("docs/API.md"))

    def test_repo_adapter_skips_default_blocked_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Public\n", encoding="utf-8")
            (root / ".env").write_text("SECRET=1\n", encoding="utf-8")
            (root / "Raw").mkdir()
            (root / "Raw" / "private.md").write_text("# Private\n", encoding="utf-8")
            registry = {
                "_path": str(root / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-security",
                        "kind": "repo_root",
                        "root": str(root),
                        "privacy": "fixture",
                        "authority": "read-only",
                        "record_owner": "tests",
                        "include": ["**/*", ".env"],
                    }
                ],
            }
            result = build_source_fragment("fixture-security", registry=registry)
            self.assertTrue(result["ok"], result)
            labels = {node["label"] for node in result["fragment"]["nodes"]}
            self.assertIn("README.md", labels)
            self.assertNotIn(".env", labels)
            self.assertNotIn("Raw/private.md", labels)

    def test_public_redaction_removes_private_paths(self) -> None:
        fragment = {
            "schema": "hapa.graph.fragment.v1",
            "source_id": "fixture",
            "nodes": [
                {
                    "id": "n1",
                    "label": "Node",
                    "type": "artifact",
                    "truth_status": "verified_source",
                    "source_id": "fixture",
                    "record_owner": "tests",
                    "privacy": "private-local",
                    "source_file": "/Users/calder/secret/file.md",
                    "record_key": "/Users/calder/secret/file.md",
                }
            ],
            "edges": [],
        }
        redacted = redact_public_fragment(fragment)
        text = str(redacted)
        self.assertNotIn("/Users/calder", text)
        self.assertIn("redacted://local/", text)
        self.assertEqual(redacted["nodes"][0]["privacy"], "private-local")
        self.assertTrue(redacted["metadata"]["public_redacted"])

    def test_export_public_dry_run_redacts_live_paths(self) -> None:
        result = export_graph(source_id="hapa-front-door-docs", dry_run=True, public=True, limit_per_source=2)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["public"])


if __name__ == "__main__":
    unittest.main()
