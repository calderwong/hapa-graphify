from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hapa_graphify.core import graph_overview


OUTPUT = ROOT / "docs" / "demo-data" / "atlas.json"


def main() -> int:
    atlas = graph_overview(kind="all", level="source_type", limit=64, edge_limit=180)
    public = {
        "schema": "hapa.graphify.pages_demo.v1",
        "kind": atlas.get("kind"),
        "level": atlas.get("level"),
        "graph": atlas.get("graph", {}),
        "nodes": [_public_node(node) for node in atlas.get("nodes", [])],
        "edges": [_public_edge(edge) for edge in atlas.get("edges", [])],
        "use": "Static public demo data. Local paths, record keys, source files, and samples are intentionally omitted.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(public, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(OUTPUT), "nodes": len(public["nodes"]), "edges": len(public["edges"])}))
    return 0


def _public_node(node: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": node.get("id"),
        "label": node.get("label"),
        "level": node.get("level"),
        "group_type": node.get("group_type"),
        "source_id": node.get("source_id"),
        "node_type": node.get("node_type"),
        "truth_status": node.get("truth_status"),
        "record_owner": node.get("record_owner"),
        "node_count": node.get("node_count", 0),
        "edge_count": node.get("edge_count", 0),
        "internal_edge_count": node.get("internal_edge_count", 0),
        "external_edge_count": node.get("external_edge_count", 0),
        "source_counts": node.get("source_counts", []),
        "type_counts": node.get("type_counts", []),
        "truth_counts": node.get("truth_counts", []),
        "owner_counts": node.get("owner_counts", []),
        "report_kinds": node.get("report_kinds", []),
    }


def _public_edge(edge: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": edge.get("id"),
        "source": edge.get("source"),
        "target": edge.get("target"),
        "type": edge.get("type"),
        "edge_count": edge.get("edge_count", 0),
        "edge_type_counts": edge.get("edge_type_counts", []),
        "truth_counts": edge.get("truth_counts", []),
    }


if __name__ == "__main__":
    raise SystemExit(main())
