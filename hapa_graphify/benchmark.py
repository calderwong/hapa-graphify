from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .core import ROOT, build_combined_graph, export_graph, path_between, query_graph
from .mcp import call_mcp_tool


def run_benchmark(*, output: str | Path | None = None, limit_per_source: int = 50) -> dict[str, Any]:
    started = time.perf_counter()
    steps = []

    def measure(name: str, fn):
        step_started = time.perf_counter()
        result = fn()
        steps.append({
            "name": name,
            "ok": bool(result.get("ok", True)),
            "duration_seconds": round(time.perf_counter() - step_started, 6),
            "summary": _summary(result),
        })
        return result

    graph = measure("build_combined_graph", lambda: build_combined_graph("all", limit_per_source=limit_per_source))
    query = measure("query_hapa_graphify", lambda: query_graph("hapa-graphify", limit=10, limit_per_source=limit_per_source))
    path = measure("path_cli_card_to_node", lambda: path_between("Build Hapa Graphify CLI parity", "hapa-graphify", limit_per_source=limit_per_source))
    export = measure("export_public_dry_run", lambda: export_graph(source_id="all", dry_run=True, public=True, limit_per_source=limit_per_source))
    guard = measure("mcp_large_graph_guard", lambda: call_mcp_tool("hapa_graph_query", {"q": "hapa", "max_nodes": 1}))

    report = {
        "ok": all(step["ok"] for step in steps[:-1]) and guard.get("error") == "graph_too_large",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "duration_seconds": round(time.perf_counter() - started, 6),
        "limit_per_source": limit_per_source,
        "baseline": {
            "node_count": graph.get("validation", {}).get("node_count", 0),
            "edge_count": graph.get("validation", {}).get("edge_count", 0),
            "query_match_count": query.get("match_count", 0),
            "path_found": path.get("found", False),
            "export_node_count": export.get("graph", {}).get("node_count", 0),
            "mcp_guard_error": guard.get("error"),
        },
        "ui_strategy": {
            "default_query_limit": 20,
            "graph_render_limit": 24,
            "large_graph_behavior": "render query result sample; use filters and explain/path instead of full-canvas load",
        },
        "steps": steps,
    }

    if output:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = (ROOT / output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        report["output"] = str(output_path)
    return report


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    if "validation" in result:
        return {
            "nodes": result["validation"].get("node_count"),
            "edges": result["validation"].get("edge_count"),
        }
    if "graph" in result:
        return result["graph"]
    return {
        key: result.get(key)
        for key in ("ok", "found", "match_count", "error", "node_count", "max_nodes")
        if key in result
    }
