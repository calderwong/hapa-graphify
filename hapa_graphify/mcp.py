from __future__ import annotations

import json
import sys
from typing import Any

from .core import (
    build_combined_graph,
    explain_graph_node,
    export_graph,
    list_sources,
    path_between,
    query_graph,
    review_suggestions_for_source,
)


MAX_TOOL_NODES = 1000

TOOL_SPECS = [
    {
        "name": "hapa_source_list",
        "description": "List registered Hapa graph sources with privacy and owner metadata.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "hapa_graph_query",
        "description": "Search graph nodes with Hapa filters before loading larger graph context.",
        "input_schema": {
            "type": "object",
            "properties": {
                "q": {"type": "string"},
                "source_id": {"type": "string"},
                "node_type": {"type": "string"},
                "truth_status": {"type": "string"},
                "record_owner": {"type": "string"},
                "privacy": {"type": "string"},
                "limit": {"type": "integer"},
                "max_nodes": {"type": "integer"},
            },
            "required": ["q"],
        },
    },
    {
        "name": "hapa_graph_path",
        "description": "Find a bounded path between two node labels or IDs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start": {"type": "string"},
                "end": {"type": "string"},
                "source_id": {"type": "string"},
                "max_depth": {"type": "integer"},
            },
            "required": ["start", "end"],
        },
    },
    {
        "name": "hapa_graph_explain",
        "description": "Explain one node with incoming and outgoing graph evidence.",
        "input_schema": {
            "type": "object",
            "properties": {
                "identifier": {"type": "string"},
                "source_id": {"type": "string"},
            },
            "required": ["identifier"],
        },
    },
    {
        "name": "hapa_review_suggestions",
        "description": "Return draft-only review cards for invalid, ambiguous, or blocked graph facts.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_id": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["source_id"],
        },
    },
    {
        "name": "hapa_export_dry_run",
        "description": "Summarize a graph export without writing output.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source_id": {"type": "string"},
                "max_nodes": {"type": "integer"},
            },
        },
    },
]


def list_mcp_tools() -> dict[str, Any]:
    return {
        "ok": True,
        "tools": TOOL_SPECS,
        "query_first_rule": "Use hapa_source_list and hapa_graph_query with filters before loading path, explain, review, or export context.",
        "max_tool_nodes": MAX_TOOL_NODES,
    }


def call_mcp_tool(name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
    arguments = arguments or {}
    if name == "hapa_source_list":
        return list_sources()
    if name == "hapa_graph_query":
        guard = _guarded_graph(arguments)
        if not guard["ok"]:
            return guard
        result = query_graph(
            str(arguments.get("q") or ""),
            source_id=str(arguments.get("source_id") or "all"),
            limit=int(arguments.get("limit") or 20),
        )
        result["matches"] = [
            item for item in result.get("matches", [])
            if _node_matches_filters(item.get("node", {}), arguments)
        ]
        result["match_count"] = len(result["matches"])
        result["filters"] = _filters(arguments)
        return result
    if name == "hapa_graph_path":
        return path_between(
            str(arguments.get("start") or ""),
            str(arguments.get("end") or ""),
            source_id=str(arguments.get("source_id") or "all"),
            max_depth=int(arguments.get("max_depth") or 6),
        )
    if name == "hapa_graph_explain":
        return explain_graph_node(
            str(arguments.get("identifier") or ""),
            source_id=str(arguments.get("source_id") or "all"),
        )
    if name == "hapa_review_suggestions":
        return review_suggestions_for_source(
            str(arguments.get("source_id") or ""),
            limit_per_table=int(arguments.get("limit") or 100),
        )
    if name == "hapa_export_dry_run":
        guard = _guarded_graph(arguments)
        if not guard["ok"]:
            return guard
        return export_graph(
            source_id=str(arguments.get("source_id") or "all"),
            dry_run=True,
            public=True,
        )
    return {"ok": False, "error": "unknown_tool", "name": name}


def run_jsonl_server(stdin=sys.stdin, stdout=sys.stdout) -> None:
    for line in stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            method = request.get("method")
            if method == "tools/list":
                result = list_mcp_tools()
            elif method == "tools/call":
                params = request.get("params") or {}
                result = call_mcp_tool(str(params.get("name") or ""), params.get("arguments") or {})
            else:
                result = {"ok": False, "error": "unknown_method", "method": method}
        except Exception as exc:  # pragma: no cover - defensive JSONL server
            result = {"ok": False, "error": str(exc)}
        stdout.write(json.dumps(result, sort_keys=True) + "\n")
        stdout.flush()


def _guarded_graph(arguments: dict[str, Any]) -> dict[str, Any]:
    max_nodes = int(arguments.get("max_nodes") or MAX_TOOL_NODES)
    source_id = str(arguments.get("source_id") or "all")
    graph = build_combined_graph(source_id, limit_per_source=int(arguments.get("limit_per_source") or 50))
    if not graph.get("ok"):
        return graph
    filtered = [
        node for node in graph["fragment"].get("nodes", [])
        if _node_matches_filters(node, arguments)
    ]
    if len(filtered) > max_nodes:
        return {
            "ok": False,
            "error": "graph_too_large",
            "node_count": len(filtered),
            "max_nodes": max_nodes,
            "filters": _filters(arguments),
            "hint": "Add source_id, node_type, truth_status, record_owner, privacy, or a narrower q.",
        }
    return {"ok": True, "node_count": len(filtered), "max_nodes": max_nodes}


def _node_matches_filters(node: dict[str, Any], arguments: dict[str, Any]) -> bool:
    filters = _filters(arguments)
    for key, value in filters.items():
        if not value:
            continue
        if str(node.get(key) or "") != str(value):
            return False
    return True


def _filters(arguments: dict[str, Any]) -> dict[str, Any]:
    source_id = arguments.get("source_id")
    return {
        "source_id": None if source_id in {None, "", "all"} else source_id,
        "type": arguments.get("node_type"),
        "truth_status": arguments.get("truth_status"),
        "record_owner": arguments.get("record_owner"),
        "privacy": arguments.get("privacy"),
    }
