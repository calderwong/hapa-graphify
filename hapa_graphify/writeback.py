from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .core import ROOT, export_graph


def plan_writeback(
    *,
    target: str = "all",
    dry_run: bool = True,
    output: str | Path | None = None,
    limit_per_source: int = 25,
) -> dict[str, Any]:
    run_id = f"hapa_graphify_writeback_{int(time.time())}"
    graph = export_graph(source_id="all", dry_run=True, public=True, limit_per_source=limit_per_source)
    graph_summary = graph.get("graph", {})
    targets = _targets(target)
    plan = {
        "ok": graph.get("ok", False),
        "run_id": run_id,
        "dry_run": dry_run,
        "requires_authorized_write": not dry_run,
        "targets": targets,
        "public_projection": True,
        "graph": graph_summary,
        "second_brain_rows": _second_brain_rows(run_id, graph_summary) if "second-brain" in targets else [],
        "lance_jsonl": _lance_rows(run_id, graph_summary) if "lance" in targets else [],
        "write_policy": {
            "dry_run_first": True,
            "mutates_second_brain": False if dry_run else "requires_authorized_writer",
            "mutates_lance": False if dry_run else "requires_authorized_writer",
            "public_paths_redacted": True,
        },
    }
    text = json.dumps(plan, sort_keys=True)
    plan["private_path_leak_count"] = text.count("/Users/")
    if output:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = (ROOT / output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
        plan["output"] = str(output_path)
    return plan


def _targets(target: str) -> list[str]:
    if target == "all":
        return ["second-brain", "lance"]
    return [item.strip() for item in target.split(",") if item.strip()]


def _second_brain_rows(run_id: str, graph_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "table": "wiki_articles",
            "operation": "upsert",
            "run_id": run_id,
            "slug": "hapa-graphify-graph-summary",
            "title": "Hapa Graphify Graph Summary",
            "article_type": "generated-graph-summary",
            "summary": f"Graph projection contains {graph_summary.get('node_count', 0)} nodes and {graph_summary.get('edge_count', 0)} edges.",
            "truth_status": "derived_or_inferred",
            "record_owner": "hapa-graphify",
        },
        {
            "table": "ecosystem_connections",
            "operation": "append",
            "run_id": run_id,
            "subject_type": "hapa_node",
            "subject_id": "hapa-graphify",
            "object_type": "knowledge_body",
            "object_id": "hapa-second-brain",
            "relation_type": "exports_public_projection",
            "truth_status": "derived_or_inferred",
            "record_owner": "hapa-graphify",
        },
    ]


def _lance_rows(run_id: str, graph_summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{run_id}:graph-summary",
            "text": f"Hapa Graphify public projection: {graph_summary.get('node_count', 0)} nodes, {graph_summary.get('edge_count', 0)} edges.",
            "metadata": {
                "run_id": run_id,
                "source": "hapa-graphify",
                "record_owner": "hapa-graphify",
                "truth_status": "derived_or_inferred",
                "privacy": "public-redacted",
                "format": "lance-jsonl-ready",
            },
        }
    ]
