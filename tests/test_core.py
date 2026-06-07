from __future__ import annotations

import unittest
import json
import sqlite3
import tempfile
from pathlib import Path

from hapa_graphify.core import (
    append_since_last_success,
    board_checkpoint,
    build_combined_graph,
    build_source_fragment,
    compute_signature_delta,
    capabilities,
    decorate_graphify_node_link,
    discover_hapa_codebases,
    explain_graph_node,
    export_graph,
    health,
    ingest_dry_run,
    list_ledger_entries,
    list_sources,
    map_graphify_confidence,
    path_between,
    query_graph,
    smoke,
    record_smoke_run,
    reconcile_against,
    review_suggestions_for_source,
    suggest_review_cards,
    stable_id,
    telemetry_probe,
    validate_graph_fragment,
    validate_sources,
)


class CoreSmokeTests(unittest.TestCase):
    def test_capabilities_shape(self) -> None:
        result = capabilities()
        self.assertTrue(result["ok"])
        self.assertEqual(result["node_id"], "hapa-graphify")
        self.assertIn("CLI", result["surfaces"])

    def test_registry_loads(self) -> None:
        result = list_sources()
        self.assertTrue(result["ok"])
        self.assertGreaterEqual(len(result["sources"]), 1)

    def test_fixture_registry_loads(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "source_registry_minimal.json"
        result = list_sources({"_path": str(fixture), "sources": [
            {
                "id": "fixture-docs",
                "kind": "markdown_root",
                "root": str(Path(__file__).parent),
                "privacy": "fixture",
                "authority": "read-only",
                "record_owner": "tests",
                "refresh_mode": "manual"
            }
        ]})
        self.assertTrue(result["ok"])
        self.assertEqual(result["sources"][0]["id"], "fixture-docs")

    def test_sources_validate(self) -> None:
        result = validate_sources()
        self.assertTrue(result["ok"], result)
        self.assertGreaterEqual(result["summary"]["source_count"], 1)

    def test_health_deep(self) -> None:
        result = health(deep=True)
        self.assertTrue(result["ok"], result)

    def test_ingest_dry_run(self) -> None:
        result = ingest_dry_run("all")
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["dry_run"])
        self.assertGreaterEqual(result["source_count"], 1)

    def test_smoke_dry_run(self) -> None:
        result = smoke(dry_run=True)
        self.assertTrue(result["ok"], result)

    def test_stable_id_avoids_private_path_leak(self) -> None:
        a = stable_id("second-brain-live", "wiki_article", "/Users/calder/secret.md", "Secret")
        b = stable_id("second-brain-live", "wiki_article", "/Users/calder/secret.md", "Secret")
        c = stable_id("second-brain-live", "wiki_article", "/Users/calder/other.md", "Secret")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertNotIn("/Users", a)

    def test_confidence_mapping(self) -> None:
        self.assertEqual(map_graphify_confidence("EXTRACTED"), "verified_source")
        self.assertEqual(map_graphify_confidence("INFERRED"), "derived_or_inferred")
        self.assertEqual(map_graphify_confidence("AMBIGUOUS"), "needs_review")
        self.assertEqual(map_graphify_confidence("weird"), "needs_review")

    def test_graph_fragment_validator_rejects_invalid_truth_status(self) -> None:
        fragment = {
            "nodes": [
                {
                    "id": "n1",
                    "label": "Node",
                    "type": "concept",
                    "truth_status": "made_up",
                    "source_id": "fixture",
                    "record_owner": "tests",
                    "privacy": "fixture",
                }
            ],
            "edges": [],
        }
        result = validate_graph_fragment(fragment)
        self.assertFalse(result["ok"])
        self.assertIn("truth_status", result["errors"][0]["path"])

    def test_golden_graph_fixture_validates(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "golden_graph_fragment.json"
        fragment = json.loads(fixture.read_text(encoding="utf-8"))
        result = validate_graph_fragment(fragment)
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["node_count"], 2)
        self.assertEqual(result["edge_count"], 1)

    def test_decorate_graphify_node_link(self) -> None:
        graph = {
            "nodes": [
                {"id": "a", "label": "Alpha", "file_type": "code", "source_file": "a.py"},
                {"id": "b", "label": "Beta", "file_type": "document", "source_file": "README.md"},
            ],
            "links": [
                {"source": "a", "target": "b", "relation": "mentions", "confidence": "EXTRACTED"}
            ],
        }
        fragment = decorate_graphify_node_link(
            graph,
            source_id="fixture",
            record_owner="tests",
            privacy="fixture",
        )
        validation = validate_graph_fragment(fragment)
        self.assertTrue(validation["ok"], validation)
        self.assertEqual(fragment["edges"][0]["truth_status"], "verified_source")

    def test_second_brain_sqlite_fragment_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "fixture.db"
            with sqlite3.connect(db_path) as db:
                db.executescript(
                    """
                    create table hapa_nodes (
                      node_id text primary key,
                      label text,
                      node_type text,
                      description text
                    );
                    create table hapa_node_skills (
                      node_skill_id text primary key,
                      node_id text,
                      label text,
                      mode text,
                      description text
                    );
                    create table ecosystem_connections (
                      connection_id text primary key,
                      subject_type text,
                      subject_id text,
                      subject_label text,
                      object_type text,
                      object_id text,
                      object_label text,
                      relation_type text,
                      score real
                    );
                    insert into hapa_nodes values ('node-a', 'Node A', 'existing_node', 'A test node');
                    insert into hapa_node_skills values ('skill-a', 'node-a', 'Using Node A', 'using', 'A test capability');
                    insert into ecosystem_connections values ('conn-a', 'topic', 'topic-a', 'Topic A', 'body', 'body-a', 'Body A', 'topic_body_shared_evidence', 9.5);
                    """
                )
            registry = {
                "_path": str(Path(tmp) / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-second-brain",
                        "kind": "sqlite",
                        "root": str(db_path),
                        "privacy": "fixture",
                        "authority": "read-only",
                        "record_owner": "tests",
                        "include": ["hapa_nodes", "hapa_node_skills", "ecosystem_connections"],
                    }
                ],
            }
            result = build_source_fragment("fixture-second-brain", limit_per_table=10, registry=registry)
            self.assertTrue(result["ok"], result)
            self.assertGreaterEqual(result["validation"]["node_count"], 4)
            self.assertGreaterEqual(result["validation"]["edge_count"], 2)

    def test_node_map_markdown_fragment_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "NODE_MAP.md").write_text(
                """
| Node | Local path | Status | Role | Ecosystem meaning |
| --- | --- | ---: | --- | --- |
| Fixture Node | ./fixture-node | Core | Test role | Test meaning |
| Missing Manifest Node | ./missing-node | Prototype | Gap role | Gap meaning |
""".strip(),
                encoding="utf-8",
            )
            (root / "fixture-node").mkdir()
            (root / "fixture-node" / "hapa-node.json").write_text(
                '{"id":"fixture-node","display_name":"Fixture Node","status":"test","role":"Fixture role","board":{"project_id":"fixture-board"}}',
                encoding="utf-8",
            )
            (root / "missing-node").mkdir()
            registry = {
                "_path": str(root / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-node-map",
                        "kind": "markdown_root",
                        "root": str(root),
                        "privacy": "fixture",
                        "authority": "read-only",
                        "record_owner": "tests",
                        "include": ["*.md", "**/hapa-node.json"],
                    }
                ],
            }
            result = build_source_fragment("fixture-node-map", limit_per_table=10, registry=registry)
            self.assertTrue(result["ok"], result)
            labels = {node["label"] for node in result["fragment"]["nodes"]}
            self.assertIn("Fixture Node", labels)
            self.assertIn("Missing manifest: Missing Manifest Node", labels)
            self.assertGreaterEqual(result["validation"]["edge_count"], 2)

    def test_kanban_project_fragment_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config" / "projects").mkdir(parents=True)
            (root / "seed").mkdir()
            (root / "data" / "fixture-board").mkdir(parents=True)
            (root / "config" / "projects" / "fixture-board.json").write_text(
                '{"id":"fixture-board","name":"Fixture Board"}',
                encoding="utf-8",
            )
            events = [
                {
                    "id": "evt-1",
                    "type": "task_created",
                    "actor": "Blue",
                    "task_id": "task-1",
                    "payload": {"title": "Task 1", "column": "ready", "owner": "Blue", "node": "hapa-graphify"},
                    "links": [{"label": "Evidence", "href": "/tmp/evidence.md"}],
                },
                {
                    "id": "evt-2",
                    "type": "review_decision",
                    "actor": "Human",
                    "task_id": "task-1",
                    "payload": {"decision": "accept"},
                },
            ]
            (root / "data" / "fixture-board" / "events.ndjson").write_text(
                "\n".join(json.dumps(event) for event in events) + "\n",
                encoding="utf-8",
            )
            (root / "seed" / "fixture-board.events.ndjson").write_text("", encoding="utf-8")
            registry = {
                "_path": str(root / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-kanban",
                        "kind": "kanban_project",
                        "root": str(root),
                        "privacy": "fixture",
                        "authority": "append-only-events",
                        "record_owner": "tests",
                        "project_id": "fixture-board",
                    }
                ],
            }
            result = build_source_fragment("fixture-kanban", limit_per_table=10, registry=registry)
            self.assertTrue(result["ok"], result)
            labels = {node["label"] for node in result["fragment"]["nodes"]}
            self.assertIn("Task 1", labels)
            self.assertIn("Review decision: accept", labels)
            self.assertGreaterEqual(result["validation"]["edge_count"], 4)

    def test_wiki_markdown_fragment_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Operations").mkdir()
            (root / "Operations" / "Protocol.md").write_text(
                """---
title: Fixture Protocol
type: operations-protocol
status: active
tags:
  - fixture
---
# Fixture Protocol

This page links to [[Related Node]] and [[Protocol Card|a card]].
""",
                encoding="utf-8",
            )
            registry = {
                "_path": str(root / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-wiki",
                        "kind": "markdown_root",
                        "root": str(root),
                        "privacy": "fixture",
                        "authority": "read-only",
                        "record_owner": "tests",
                        "include": ["**/*.md"],
                    }
                ],
            }
            result = build_source_fragment("fixture-wiki", limit_per_table=10, registry=registry)
            self.assertTrue(result["ok"], result)
            labels = {node["label"] for node in result["fragment"]["nodes"]}
            self.assertIn("Fixture Protocol", labels)
            self.assertIn("Related Node", labels)
            self.assertIn("Protocol Card", labels)
            self.assertIn("Fixture Protocol", labels)
            self.assertGreaterEqual(result["validation"]["edge_count"], 4)
            self.assertEqual(result["fragment"]["metadata"]["markdown_pages_selected"], 1)

    def test_wiki_markdown_fragment_full_mode_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Protocols").mkdir()
            for index in range(3):
                (root / "Protocols" / f"Protocol {index}.md").write_text(
                    f"# Protocol {index}\n\n## Step {index}\n\nLinks to [[Shared Concept]].\n",
                    encoding="utf-8",
                )
            registry = {
                "_path": str(root / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-wiki-full",
                        "kind": "markdown_root",
                        "root": str(root),
                        "privacy": "fixture",
                        "authority": "read-only",
                        "record_owner": "tests",
                        "include": ["**/*.md"],
                    }
                ],
            }
            result = build_source_fragment("fixture-wiki-full", limit_per_table=0, registry=registry)
            self.assertTrue(result["ok"], result)
            self.assertEqual(result["fragment"]["metadata"]["markdown_pages_selected"], 3)
            self.assertGreaterEqual(result["fragment"]["metadata"]["directory_nodes"], 1)
            self.assertGreaterEqual(result["fragment"]["metadata"]["heading_nodes"], 3)

    def test_repo_root_fragment_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Fixture Repo\n", encoding="utf-8")
            (root / "AGENTS.md").write_text("# Agent Guide\n", encoding="utf-8")
            (root / "private.db-wal").write_text("private", encoding="utf-8")
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("def main():\n    return True\n", encoding="utf-8")
            registry = {
                "_path": str(root / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-repo",
                        "kind": "repo_root",
                        "root": str(root),
                        "privacy": "fixture",
                        "authority": "read-only",
                        "record_owner": "tests",
                        "include": ["README.md", "AGENTS.md", "src/**/*.py"],
                        "exclude": ["*.db-wal"],
                    }
                ],
            }
            result = build_source_fragment("fixture-repo", limit_per_table=10, registry=registry)
            self.assertTrue(result["ok"], result)
            labels = {node["label"] for node in result["fragment"]["nodes"]}
            self.assertIn("README.md", labels)
            self.assertIn("AGENTS.md", labels)
            self.assertIn("src/app.py", labels)
            self.assertNotIn("private.db-wal", labels)

    def test_hapa_codebase_discovery_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            node = root / "hapa-node-a"
            nested = node / "packages" / "worker"
            nested.mkdir(parents=True)
            (node / "package.json").write_text('{"name":"hapa-node-a"}', encoding="utf-8")
            (node / "hapa-node.json").write_text('{"id":"hapa-node-a","display_name":"Node A"}', encoding="utf-8")
            (nested / "pyproject.toml").write_text("[project]\nname='worker'\n", encoding="utf-8")
            (nested / "worker.py").write_text("def run():\n    return True\n", encoding="utf-8")
            (node / "node_modules" / "leftpad").mkdir(parents=True)
            (node / "node_modules" / "leftpad" / "package.json").write_text("{}", encoding="utf-8")
            node_map = root / "NODE_MAP.md"
            node_map.write_text(
                """
| Node | Local path | Status | Role | Ecosystem meaning |
|---|---|---:|---|---|
| Node A | ./hapa-node-a | Core | Test node | Test ecosystem node |
""".strip(),
                encoding="utf-8",
            )
            audit = root / "audit.json"
            audit.write_text('{"audit":[]}', encoding="utf-8")
            configs = root / "configs"
            configs.mkdir()
            result = discover_hapa_codebases(
                node_map_path=node_map,
                quest_audit_path=audit,
                overwatch_config_dir=configs,
            )
            self.assertTrue(result["ok"], result)
            paths = {Path(item["path"]).name for item in result["codebases"]}
            self.assertIn("hapa-node-a", paths)
            self.assertIn("worker", paths)
            self.assertNotIn("leftpad", paths)

    def test_run_ledger_records_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "runs.ndjson"
            result = record_smoke_run(dry_run=True, ledger_path=ledger)
            self.assertTrue(result["ok"], result)
            self.assertTrue(ledger.exists())
            listed = list_ledger_entries(ledger_path=ledger)
            self.assertTrue(listed["ok"])
            self.assertEqual(len(listed["entries"]), 1)
            self.assertFalse(listed["entries"][0]["graph_changed"])
            self.assertGreaterEqual(len(listed["entries"][0]["source_signatures"]), 1)

    def test_signature_delta_has_tombstone_candidates(self) -> None:
        delta = compute_signature_delta({"a": "old", "removed": "gone"}, {"a": "new", "b": "fresh"})
        self.assertIn("b", delta["added"])
        self.assertIn("a", delta["changed"])
        self.assertIn("removed", delta["removed"])

    def test_append_since_last_success_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "runs.ndjson"
            record_smoke_run(dry_run=True, ledger_path=ledger)
            result = append_since_last_success(dry_run=True, ledger_path=ledger)
            self.assertTrue(result["ok"], result)
            self.assertFalse(result["graph_changed"])
            self.assertIn("delta", result)
            self.assertIn("tombstone_candidates", result)

    def test_review_suggestions_are_draft_only(self) -> None:
        fragment = {
            "schema": "hapa.graph.fragment.v1",
            "source_id": "fixture",
            "nodes": [
                {
                    "id": "n1",
                    "label": "Ambiguous Node",
                    "type": "concept",
                    "truth_status": "needs_review",
                    "source_id": "fixture",
                    "record_owner": "tests",
                    "privacy": "fixture",
                }
            ],
            "edges": [],
        }
        result = suggest_review_cards(fragment)
        self.assertTrue(result["draft_only"])
        self.assertTrue(result["authorized_append_required"])
        self.assertEqual(result["draft_card_count"], 1)

    def test_review_suggestions_for_source(self) -> None:
        result = review_suggestions_for_source("hapa-front-door-docs", limit_per_table=5)
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["draft_only"])

    def test_telemetry_probe_blocks_non_loopback(self) -> None:
        result = telemetry_probe(["https://example.com/health?token=secret"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["blocked_count"], 1)
        self.assertEqual(result["probes"][0]["error"], "non_loopback_blocked")
        self.assertEqual(result["fragment"]["nodes"][0]["truth_status"], "blocked")
        self.assertNotIn("token=secret", result["fragment"]["nodes"][0]["label"])

    def test_telemetry_probe_loopback_offline_is_blocked(self) -> None:
        result = telemetry_probe(["http://127.0.0.1:9/health"])
        self.assertTrue(result["ok"], result)
        self.assertEqual(result["blocked_count"], 1)
        self.assertEqual(result["probes"][0]["status"], "offline_or_unreachable")
        self.assertEqual(result["fragment"]["nodes"][0]["truth_status"], "blocked")
        self.assertIn("observed_at", result["fragment"]["nodes"][0])
        self.assertFalse(result["fragment"]["nodes"][0]["token_files_read"])

    def test_combined_query_path_and_explain_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Alpha.md").write_text("# Alpha\n\nLinks to [[Beta]].\n", encoding="utf-8")
            registry = {
                "_path": str(root / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-graph",
                        "kind": "markdown_root",
                        "root": str(root),
                        "privacy": "fixture",
                        "authority": "read-only",
                        "record_owner": "tests",
                        "include": ["**/*.md"],
                    }
                ],
            }
            combined = build_combined_graph("all", registry=registry)
            self.assertTrue(combined["ok"], combined)
            queried = query_graph("Alpha", registry=registry)
            self.assertTrue(queried["ok"], queried)
            self.assertGreaterEqual(queried["match_count"], 1)
            path = path_between("Alpha", "Beta", registry=registry)
            self.assertTrue(path["ok"], path)
            self.assertTrue(path["found"], path)
            explained = explain_graph_node("Alpha", registry=registry)
            self.assertTrue(explained["found"], explained)
            self.assertGreaterEqual(explained["outgoing_count"], 1)

    def test_export_graph_dry_run_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Alpha.md").write_text("# Alpha\n", encoding="utf-8")
            registry = {
                "_path": str(root / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-export",
                        "kind": "markdown_root",
                        "root": str(root),
                        "privacy": "fixture",
                        "authority": "read-only",
                        "record_owner": "tests",
                        "include": ["**/*.md"],
                    }
                ],
            }
            result = export_graph(source_id="fixture-export", output=root / "out.json", dry_run=True, registry=registry)
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["would_write"])
            self.assertFalse((root / "out.json").exists())

    def test_reconcile_and_board_checkpoint_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = reconcile_against("second-brain", dry_run=True, ledger_path=Path(tmp) / "runs.ndjson")
            self.assertTrue(result["ok"], result)
            self.assertTrue(result["dry_run"])
            root = Path(tmp)
            registry = {
                "_path": str(root / "registry.json"),
                "sources": [
                    {
                        "id": "fixture-kanban",
                        "kind": "kanban_project",
                        "root": str(root),
                        "privacy": "fixture",
                        "authority": "append-only-events",
                        "record_owner": "tests",
                        "project_id": "hapa-app-hapa-graphify",
                    }
                ],
            }
            checkpoint = board_checkpoint("fixture message", dry_run=True, registry=registry)
            self.assertTrue(checkpoint["ok"], checkpoint)
            self.assertTrue(checkpoint["would_append"])
            self.assertFalse((root / "data" / "hapa-app-hapa-graphify" / "events.ndjson").exists())


if __name__ == "__main__":
    unittest.main()
