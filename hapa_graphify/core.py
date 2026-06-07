from __future__ import annotations

import fnmatch
import copy
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from . import __version__

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "config" / "hapa-graphify.sources.json"
DEFAULT_RUN_LEDGER = ROOT / "runs" / "hapa-graphify-runs.ndjson"
DEFAULT_EXPORT_DIR = ROOT / "exports"
DEFAULT_NODE_MAP = Path(os.path.expandvars(os.environ.get("HAPA_NODE_MAP", "$HOME/Desktop/hapa/docs/NODE_MAP.md"))).expanduser()
DEFAULT_QUEST_KEEPER_AUDIT = Path(os.path.expandvars(os.environ.get("HAPA_QUEST_KEEPER_AUDIT", "$HOME/Desktop/hapa-quest-keeper/artifacts/audit/hapa-node-kanban-audit.json"))).expanduser()
DEFAULT_OVERWATCH_CONFIG_DIR = Path(os.path.expandvars(os.environ.get("HAPA_OVERWATCH_CONFIG_DIR", "$HOME/Documents/Codex/2026-05-27/can-you-generate-me-some-concept/hapa-overwatch-kanban/config/projects"))).expanduser()
DEFAULT_GRAPHIFY_UPSTREAM = ROOT.parent / "graphify"
DEFAULT_ECOSYSTEM_SAMPLE_CODEBASES = 10
DEFAULT_HAPA_SECOND_BRAIN_DB = Path(os.path.expandvars(os.environ.get("HAPA_SECOND_BRAIN_DB", "$HOME/Documents/Codex/2026-05-25/can-you-grab-my-1-amazon/hapa_second_brain/hapa_second_brain.db"))).expanduser()
DEFAULT_HAPA_WIKI_ROOT = Path(os.path.expandvars(os.environ.get("HAPA_WIKI_ROOT", "$HOME/Desktop/Hapa_Worldbuilding_Wiki"))).expanduser()
DEFAULT_KNOWLEDGE_SOURCE_IDS = [
    "second-brain-live",
    "hapa-front-door-docs",
    "worldbuilding-wiki-full",
    "worldbuilding-wiki-operations",
    "quest-keeper-audits",
    "overwatch-kanban-hapa-graphify",
]
MAP_LEVELS = ("community", "type", "source_type", "truth", "owner")
MAP_GROUP_SAMPLE_SIZE = 12

HAPA_PATH_DEFAULTS = {
    "HAPA_DESKTOP_ROOT": "$HOME/Desktop",
    "HAPA_FRONT_DOOR_DOCS": "$HOME/Desktop/hapa/docs",
    "HAPA_MLX_STATION_ROOT": "$HOME/hapa-mlx-station",
    "HAPA_NODE_MAP": "$HOME/Desktop/hapa/docs/NODE_MAP.md",
    "HAPA_OVERWATCH_CONFIG_DIR": "$HOME/Documents/Codex/2026-05-27/can-you-generate-me-some-concept/hapa-overwatch-kanban/config/projects",
    "HAPA_OVERWATCH_ROOT": "$HOME/Documents/Codex/2026-05-27/can-you-generate-me-some-concept/hapa-overwatch-kanban",
    "HAPA_QUEST_KEEPER_AUDIT": "$HOME/Desktop/hapa-quest-keeper/artifacts/audit/hapa-node-kanban-audit.json",
    "HAPA_QUEST_KEEPER_AUDIT_ROOT": "$HOME/Desktop/hapa-quest-keeper/artifacts/audit",
    "HAPA_SECOND_BRAIN_DB": "$HOME/Documents/Codex/2026-05-25/can-you-grab-my-1-amazon/hapa_second_brain/hapa_second_brain.db",
    "HAPA_WIKI_OPERATIONS_ROOT": "$HOME/Desktop/Hapa_Worldbuilding_Wiki/Operations",
    "HAPA_WIKI_ROOT": "$HOME/Desktop/Hapa_Worldbuilding_Wiki",
}

CODEBASE_MARKERS = {
    "package.json",
    "pyproject.toml",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Package.swift",
    "composer.json",
    "Gemfile",
    "deno.json",
    "deno.jsonc",
    "hapa-node.json",
}

CODE_EXTENSIONS = {
    ".py", ".pyi", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".go", ".rs",
    ".java", ".groovy", ".gradle", ".cpp", ".cc", ".cxx", ".c", ".h", ".hpp",
    ".rb", ".swift", ".kt", ".kts", ".cs", ".scala", ".php", ".lua", ".luau",
    ".zig", ".ps1", ".ex", ".exs", ".m", ".mm", ".jl", ".vue", ".svelte",
    ".astro", ".dart", ".sql", ".sh", ".bash", ".json", ".tf", ".tfvars",
    ".hcl", ".sln", ".csproj", ".fsproj", ".vbproj", ".razor", ".cshtml",
}

CODEBASE_SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "dist", "build", ".next", ".nuxt",
    ".svelte-kit", ".venv", "venv", "__pycache__", ".pytest_cache", ".mypy_cache",
    ".ruff_cache", ".cache", ".build", ".conda-env", "conda", "checkouts", "vendor", "vendors", "Pods",
    "site-packages", ".dart_tool", ".terraform", ".serverless", "tmp", "Temp", "Library",
    "DerivedData", "public/generated", "Raw", "Private", "graphify-out", "upstream",
}

_DISCOVERY_CACHE: dict[tuple[Any, ...], dict[str, Any]] = {}

NODE_TYPES = {
    "hapa_node",
    "repo",
    "source_file",
    "capability",
    "skill",
    "agent",
    "protocol_card",
    "wiki_article",
    "turn_card",
    "kanban_card",
    "artifact",
    "endpoint",
    "concept",
}

EDGE_TYPES = {
    "implements",
    "owns_record",
    "tracks",
    "depends_on",
    "indexes",
    "mentions",
    "derived_from",
    "uses_skill",
    "relates_to",
    "calls",
    "imports",
    "defines",
    "routes_to",
    "blocked_by",
}

TRUTH_STATUSES = {
    "verified_source",
    "verified_runtime",
    "derived_or_inferred",
    "needs_review",
    "blocked",
}

GRAPHIFY_CONFIDENCE_TO_HAPA = {
    "EXTRACTED": "verified_source",
    "INFERRED": "derived_or_inferred",
    "AMBIGUOUS": "needs_review",
}


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    registry_path = Path(path or os.environ.get("HAPA_GRAPHIFY_SOURCE_REGISTRY", DEFAULT_REGISTRY))
    if not registry_path.is_absolute():
        registry_path = (ROOT / registry_path).resolve()
    return json.loads(registry_path.read_text(encoding="utf-8")) | {
        "_path": str(registry_path)
    }


def capabilities() -> dict[str, Any]:
    return {
        "ok": True,
        "node_id": "hapa-graphify",
        "version": __version__,
        "surfaces": ["CLI", "API", "UI", "MCP", "DESKTOP", "DATA", "DOCS"],
        "commands": [
            "health",
            "capabilities",
            "smoke",
            "sources list",
            "sources validate",
            "ingest --dry-run",
            "fragment",
            "ledger record-smoke",
            "ledger list",
            "append --since last-success --dry-run",
            "reconcile --against second-brain --dry-run",
            "query",
            "map",
            "path",
            "explain",
            "export --dry-run",
            "reports list",
            "board checkpoint --dry-run",
            "review-suggestions",
            "telemetry probe",
            "ecosystem discover",
            "ecosystem ast --full",
            "knowledge graph --full",
            "narrative run",
            "serve",
            "mcp tools",
            "mcp call",
            "mcp serve-jsonl",
            "benchmark",
            "writeback --dry-run",
        ],
        "truth_statuses": [
            *sorted(TRUTH_STATUSES)
        ],
        "board_project_id": "hapa-app-hapa-graphify",
        "graphify_engine": {
            "strategy": "optional-wrapper",
            "package": "graphifyy",
            "reviewed_version": "0.8.33",
            "reviewed_commit": "4b06fd7bf7e1e407d8acb4dd9a1404e21cf34bce",
            "ast_dependency": "tree-sitter"
        }
    }


def stable_id(
    source_id: str,
    record_type: str,
    record_key: str,
    label: str,
    source_location: str | None = None,
) -> str:
    """Create a deterministic Hapa graph id without embedding private paths."""
    parts = [source_id, record_type, record_key, label, source_location or ""]
    digest = hashlib.sha256("\u241f".join(_normalize_token(part) for part in parts).encode("utf-8")).hexdigest()
    return f"{_normalize_token(source_id)}:{_normalize_token(record_type)}:{digest[:16]}"


def map_graphify_confidence(confidence: str | None) -> str:
    if not confidence:
        return "derived_or_inferred"
    return GRAPHIFY_CONFIDENCE_TO_HAPA.get(str(confidence).upper(), "needs_review")


def validate_graph_fragment(fragment: dict[str, Any]) -> dict[str, Any]:
    """Validate a Hapa graph fragment before build/export/writeback."""
    errors: list[dict[str, Any]] = []
    nodes = fragment.get("nodes", [])
    edges = fragment.get("edges", fragment.get("links", []))
    node_ids = set()

    if not isinstance(nodes, list):
        errors.append({"path": "nodes", "error": "nodes must be a list"})
        nodes = []
    if not isinstance(edges, list):
        errors.append({"path": "edges", "error": "edges must be a list"})
        edges = []

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            errors.append({"path": f"nodes[{index}]", "error": "node must be an object"})
            continue
        node_id = node.get("id")
        if not node_id:
            errors.append({"path": f"nodes[{index}].id", "error": "id is required"})
        else:
            node_ids.add(node_id)
        if node.get("type") not in NODE_TYPES:
            errors.append({"path": f"nodes[{index}].type", "error": f"invalid node type: {node.get('type')}"})
        if node.get("truth_status") not in TRUTH_STATUSES:
            errors.append({
                "path": f"nodes[{index}].truth_status",
                "error": f"invalid truth status: {node.get('truth_status')}"
            })
        for field in ("label", "source_id", "record_owner", "privacy"):
            if not node.get(field):
                errors.append({"path": f"nodes[{index}].{field}", "error": f"{field} is required"})

    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            errors.append({"path": f"edges[{index}]", "error": "edge must be an object"})
            continue
        src = edge.get("source", edge.get("from"))
        tgt = edge.get("target", edge.get("to"))
        if src not in node_ids:
            errors.append({"path": f"edges[{index}].source", "error": f"unknown source: {src}"})
        if tgt not in node_ids:
            errors.append({"path": f"edges[{index}].target", "error": f"unknown target: {tgt}"})
        if edge.get("type", edge.get("relation")) not in EDGE_TYPES:
            errors.append({"path": f"edges[{index}].type", "error": f"invalid edge type: {edge.get('type', edge.get('relation'))}"})
        if edge.get("truth_status") not in TRUTH_STATUSES:
            errors.append({
                "path": f"edges[{index}].truth_status",
                "error": f"invalid truth status: {edge.get('truth_status')}"
            })
    return {
        "ok": not errors,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "errors": errors,
    }


def suggest_review_cards(fragment: dict[str, Any], validation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return draft-only board cards for ambiguous, blocked, or invalid graph facts."""
    validation = validation or validate_graph_fragment(fragment)
    draft_cards: list[dict[str, Any]] = []
    for error in validation.get("errors", []):
        draft_cards.append({
            "draft_only": True,
            "authorized_append_required": True,
            "title": f"Review invalid graph fragment: {error.get('path')}",
            "description": error.get("error"),
            "priority": "P0",
            "lane": "Graph Review",
            "truth_status": "needs_review",
            "evidence": {"path": error.get("path"), "error": error.get("error")},
        })

    for collection_name in ("nodes", "edges"):
        for index, item in enumerate(fragment.get(collection_name, [])):
            truth = item.get("truth_status")
            if truth not in {"needs_review", "blocked"}:
                continue
            label = item.get("label") or item.get("relation") or item.get("type") or f"{collection_name}[{index}]"
            draft_cards.append({
                "draft_only": True,
                "authorized_append_required": True,
                "title": f"Review {truth} graph fact: {label}",
                "description": "Graph fact needs review before promotion or writeback.",
                "priority": "P1" if truth == "needs_review" else "P0",
                "lane": "Graph Review",
                "truth_status": truth,
                "evidence": {
                    "collection": collection_name,
                    "index": index,
                    "item": item,
                },
            })
    return {
        "ok": True,
        "draft_only": True,
        "authorized_append_required": True,
        "draft_card_count": len(draft_cards),
        "draft_cards": draft_cards,
    }


def decorate_graphify_node_link(
    graph: dict[str, Any],
    *,
    source_id: str,
    record_owner: str,
    privacy: str,
) -> dict[str, Any]:
    """Convert generic Graphify node-link data into a Hapa graph fragment."""
    nodes = []
    id_map: dict[str, str] = {}
    for node in graph.get("nodes", []):
        original_id = str(node.get("id", node.get("label", "")))
        label = str(node.get("label") or original_id)
        hapa_id = stable_id(source_id, "concept", original_id, label, node.get("source_location"))
        id_map[original_id] = hapa_id
        nodes.append({
            "id": hapa_id,
            "label": label,
            "type": _graphify_file_type_to_hapa(node.get("file_type")),
            "truth_status": "verified_source" if node.get("source_file") else "derived_or_inferred",
            "source_id": source_id,
            "record_owner": record_owner,
            "privacy": privacy,
            "source_file": node.get("source_file"),
            "source_location": node.get("source_location"),
            "upstream_id": original_id,
        })

    edges = []
    for edge in graph.get("edges", graph.get("links", [])):
        src = str(edge.get("source", edge.get("from", "")))
        tgt = str(edge.get("target", edge.get("to", "")))
        if src not in id_map or tgt not in id_map:
            continue
        relation = str(edge.get("relation", "relates_to"))
        edges.append({
            "source": id_map[src],
            "target": id_map[tgt],
            "type": relation if relation in EDGE_TYPES else "relates_to",
            "relation": relation,
            "truth_status": map_graphify_confidence(edge.get("confidence")),
            "source_id": source_id,
            "record_owner": record_owner,
            "privacy": privacy,
            "confidence": edge.get("confidence"),
            "confidence_score": edge.get("confidence_score"),
        })
    return {
        "schema": "hapa.graph.fragment.v1",
        "source_id": source_id,
        "nodes": nodes,
        "edges": edges,
    }


def health(deep: bool = False) -> dict[str, Any]:
    registry = load_registry()
    checks = [
        {"name": "source_registry_exists", "ok": Path(registry["_path"]).exists(), "path": registry["_path"]},
        {"name": "docs_exist", "ok": (ROOT / "docs").is_dir(), "path": str(ROOT / "docs")},
        {"name": "manifest_exists", "ok": (ROOT / "hapa-node.json").exists(), "path": str(ROOT / "hapa-node.json")},
    ]
    if deep:
        validation = validate_sources(registry)
        checks.append({
            "name": "source_registry_validates",
            "ok": validation["ok"],
            "summary": validation["summary"],
        })
    return {
        "ok": all(item["ok"] for item in checks),
        "node_id": "hapa-graphify",
        "version": __version__,
        "deep": deep,
        "checks": checks,
    }


def list_sources(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or load_registry()
    sources = []
    for source in registry.get("sources", []):
        sources.append({
            "id": source["id"],
            "kind": source["kind"],
            "root": resolve_source_root(source),
            "privacy": source.get("privacy", registry.get("default_privacy")),
            "authority": source.get("authority", registry.get("default_authority")),
            "record_owner": source.get("record_owner"),
            "refresh_mode": source.get("refresh_mode"),
        })
    return {"ok": True, "registry": registry["_path"], "sources": sources}


def validate_sources(registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or load_registry()
    results = []
    for source in registry.get("sources", []):
        root = Path(resolve_source_root(source))
        result = {
            "id": source.get("id"),
            "kind": source.get("kind"),
            "root": str(root),
            "exists": root.exists(),
            "ok": root.exists(),
            "warnings": [],
        }
        if source.get("kind") == "sqlite" and root.exists():
            result.update(_validate_sqlite_source(root, source))
        elif source.get("kind") == "kanban_project" and root.exists():
            project_id = source.get("project_id")
            required = [
                root / "config" / "projects" / f"{project_id}.json",
                root / "seed" / f"{project_id}.events.ndjson",
            ]
            missing = [str(p) for p in required if not p.exists()]
            result["ok"] = not missing
            result["missing"] = missing
        results.append(result)
    return {
        "ok": all(item["ok"] for item in results),
        "registry": registry["_path"],
        "summary": {
            "source_count": len(results),
            "ok_count": sum(1 for item in results if item["ok"]),
            "missing_count": sum(1 for item in results if not item["ok"]),
        },
        "results": results,
    }


def ingest_dry_run(source_id: str = "all", registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry = registry or load_registry()
    selected = [
        source for source in registry.get("sources", [])
        if source_id == "all" or source.get("id") == source_id
    ]
    if not selected:
        return {"ok": False, "error": f"Unknown source: {source_id}", "source_id": source_id}

    run_id = f"hg_dry_{int(time.time())}"
    summaries = []
    for source in selected:
        summaries.append(_summarize_source(source, registry))
    return {
        "ok": all(summary["ok"] for summary in summaries),
        "dry_run": True,
        "run_id": run_id,
        "source_id": source_id,
        "source_count": len(summaries),
        "changed": False,
        "summaries": summaries,
    }


def discover_hapa_codebases(
    *,
    node_map_path: str | Path | None = None,
    quest_audit_path: str | Path | None = None,
    overwatch_config_dir: str | Path | None = None,
    manifest_scan_roots: list[str | Path] | None = None,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Discover Hapa node roots and nested codebases from current local authority sources."""
    node_map = Path(node_map_path or DEFAULT_NODE_MAP)
    quest_audit = Path(quest_audit_path or DEFAULT_QUEST_KEEPER_AUDIT)
    config_dir = Path(overwatch_config_dir or DEFAULT_OVERWATCH_CONFIG_DIR)
    cache_key = (
        str(node_map),
        str(quest_audit),
        str(config_dir),
        tuple(str(item) for item in (manifest_scan_roots or [])),
        tuple((name, os.environ.get(name, default)) for name, default in sorted(HAPA_PATH_DEFAULTS.items())),
    )
    if use_cache and cache_key in _DISCOVERY_CACHE:
        return copy.deepcopy(_DISCOVERY_CACHE[cache_key])
    candidates: dict[str, dict[str, Any]] = {}

    def add_candidate(
        *,
        node_id: str,
        path_value: str | Path,
        name: str | None = None,
        status: str | None = None,
        role: str | None = None,
        source: str,
        meaning: str | None = None,
        project_id: str | None = None,
    ) -> None:
        resolved = _resolve_hapa_path(path_value, base=node_map.parent if node_map.exists() else Path.cwd())
        if not resolved:
            return
        key = str(resolved)
        existing = candidates.setdefault(key, {
            "node_id": _normalize_node_id(node_id or name or resolved.name),
            "name": name or node_id or resolved.name,
            "path": key,
            "exists": resolved.exists(),
            "is_dir": resolved.is_dir(),
            "status": status,
            "role": role,
            "meaning": meaning,
            "project_id": project_id,
            "sources": [],
        })
        if source not in existing["sources"]:
            existing["sources"].append(source)
        for field, value in {
            "status": status,
            "role": role,
            "meaning": meaning,
            "project_id": project_id,
            "name": name,
        }.items():
            if value and not existing.get(field):
                existing[field] = value

    if node_map.exists():
        for row in _parse_node_map_rows(node_map):
            local_path = row.get("Local path") or row.get("Path") or ""
            node_name = row.get("Node") or row.get("Name") or ""
            if not local_path or node_name in {"Node", "---"}:
                continue
            add_candidate(
                node_id=node_name,
                name=node_name,
                path_value=local_path,
                status=row.get("Status"),
                role=row.get("Role"),
                meaning=row.get("Ecosystem meaning"),
                source="node-map",
            )

    if quest_audit.exists():
        try:
            audit = json.loads(quest_audit.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            audit = {}
        for row in audit.get("audit", []) if isinstance(audit, dict) else []:
            node = row.get("node") if isinstance(row, dict) else None
            if not isinstance(node, dict):
                continue
            node_path = node.get("path")
            if not node_path:
                continue
            add_candidate(
                node_id=str(node.get("id") or node.get("name") or Path(str(node_path)).name),
                name=node.get("name") or node.get("id"),
                path_value=str(node_path),
                status=node.get("status"),
                role=node.get("role"),
                meaning=node.get("meaning"),
                source="quest-keeper-audit",
                project_id=row.get("expected_project_id"),
            )

    if config_dir.exists():
        for config_path in sorted(config_dir.glob("*.json")):
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            quest = config.get("protocol", {}).get("questKeeper", {})
            if not isinstance(quest, dict) or not quest.get("nodePath"):
                continue
            add_candidate(
                node_id=str(quest.get("nodeId") or config.get("id") or config_path.stem),
                name=quest.get("nodeId") or config.get("name"),
                path_value=str(quest["nodePath"]),
                source="overwatch-config",
                project_id=config.get("id"),
            )

    scan_roots = [Path(item) for item in (manifest_scan_roots or [])]
    for scan_root in _dedupe_paths(scan_roots):
        for manifest in _iter_hapa_manifests(scan_root):
            try:
                manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                manifest_data = {}
            add_candidate(
                node_id=str(manifest_data.get("id") or manifest.parent.name),
                name=manifest_data.get("display_name") or manifest_data.get("name") or manifest.parent.name,
                path_value=manifest.parent,
                status=manifest_data.get("status"),
                role=manifest_data.get("role"),
                source="hapa-node-manifest",
                project_id=(manifest_data.get("board") or {}).get("project_id") if isinstance(manifest_data.get("board"), dict) else None,
            )

    node_roots = sorted(candidates.values(), key=lambda item: (str(item.get("node_id")), str(item.get("path"))))
    codebases = _discover_codebase_roots(node_roots)
    result = {
        "ok": True,
        "node_root_count": len(node_roots),
        "codebase_count": len(codebases),
        "missing_count": sum(1 for item in node_roots if not item.get("exists")),
        "node_roots": node_roots,
        "codebases": codebases,
        "sources": {
            "node_map": str(node_map),
            "quest_audit": str(quest_audit),
            "overwatch_config_dir": str(config_dir),
        },
    }
    if use_cache:
        _DISCOVERY_CACHE[cache_key] = copy.deepcopy(result)
    return result


def run_hapa_ecosystem_ast_analysis(
    *,
    full: bool = False,
    limit_per_codebase: int = 50,
    max_codebases: int | None = None,
    output: str | Path | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry or load_registry()
    source = next((item for item in registry.get("sources", []) if item.get("id") == "hapa-ecosystem-codebases"), None)
    if source is None:
        source = _default_hapa_ecosystem_source()
    is_full = full or limit_per_codebase <= 0
    effective_max_codebases = _ecosystem_sample_codebase_limit(
        full=is_full,
        limit_per_codebase=limit_per_codebase,
        max_codebases=max_codebases,
    )
    fragment_result = _hapa_ecosystem_codebases_fragment(
        source,
        limit_per_codebase=limit_per_codebase,
        full=is_full,
        max_codebases=effective_max_codebases,
    )
    fragment = fragment_result["fragment"]
    validation = validate_graph_fragment(fragment)
    report = {
        "ok": fragment_result.get("ok", False) and validation["ok"],
        "run_id": f"hapa_ecosystem_ast_{int(time.time())}",
        "full": is_full,
        "limit_per_codebase": limit_per_codebase,
        "max_codebases": effective_max_codebases,
        "graph": _graph_summary(fragment),
        "validation": validation,
        "discovery": fragment_result.get("discovery"),
        "ast": fragment_result.get("ast"),
        "errors": fragment_result.get("errors", []),
    }
    if output:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = (ROOT / output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "hapa.graph.fragment.v1",
            "report": report,
            "graph": fragment,
        }
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        _write_report_summary(output_path, report, fragment)
        report["output"] = str(output_path)
        report["wrote"] = True
    else:
        report["wrote"] = False
    return report


def _ecosystem_sample_codebase_limit(
    *,
    full: bool,
    limit_per_codebase: int,
    max_codebases: int | None,
) -> int | None:
    if max_codebases is not None:
        return max_codebases
    if full:
        return None
    sample_size = limit_per_codebase if limit_per_codebase > 0 else DEFAULT_ECOSYSTEM_SAMPLE_CODEBASES
    return max(1, min(sample_size, DEFAULT_ECOSYSTEM_SAMPLE_CODEBASES))


def run_hapa_knowledge_analysis(
    *,
    full: bool = False,
    limit_per_source: int = 100,
    output: str | Path | None = None,
    source_ids: list[str] | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry or load_registry()
    selected_ids = source_ids or DEFAULT_KNOWLEDGE_SOURCE_IDS
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    source_results: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    effective_limit = 0 if full else limit_per_source

    for source_id in selected_ids:
        result = build_source_fragment(
            source_id,
            limit_per_table=effective_limit,
            full=full,
            registry=registry,
        )
        fragment = result.get("fragment") or {}
        validation = result.get("validation") or {}
        source_results.append({
            "source_id": source_id,
            "ok": result.get("ok"),
            "validation": validation,
            "metadata": fragment.get("metadata", {}),
            "error": result.get("error"),
        })
        if not result.get("ok"):
            errors.append({"source_id": source_id, "error": result.get("error"), "validation": validation})
            continue
        for node in fragment.get("nodes", []):
            nodes_by_id.setdefault(node["id"], node)
        for edge in fragment.get("edges", []):
            key = (
                str(edge.get("source")),
                str(edge.get("target")),
                str(edge.get("type")),
                str(edge.get("source_id")),
                str(edge.get("relation", "")),
            )
            edges_by_key.setdefault(key, edge)

    fragment = {
        "schema": "hapa.graph.fragment.v1",
        "source_id": "hapa-knowledge",
        "nodes": list(nodes_by_id.values()),
        "edges": list(edges_by_key.values()),
        "metadata": {
            "full": full,
            "limit_per_source": limit_per_source,
            "source_ids": selected_ids,
            "purpose": "Second Brain, wiki, protocol, markdown, documentation, and board knowledge graph",
        },
    }
    validation = validate_graph_fragment(fragment)
    report = {
        "ok": validation["ok"] and not errors,
        "run_id": f"hapa_knowledge_{int(time.time())}",
        "full": full,
        "limit_per_source": limit_per_source,
        "source_ids": selected_ids,
        "graph": _graph_summary(fragment),
        "validation": validation,
        "sources": source_results,
        "errors": errors,
    }
    if output:
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = (ROOT / output_path).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "hapa.graph.fragment.v1",
            "report": report,
            "graph": fragment,
        }
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        _write_report_summary(output_path, report, fragment)
        report["output"] = str(output_path)
        report["wrote"] = True
    else:
        report["wrote"] = False
    return report


def build_source_fragment(
    source_id: str,
    *,
    limit_per_table: int = 100,
    full: bool = False,
    max_codebases: int | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry or load_registry()
    source = next((item for item in registry.get("sources", []) if item.get("id") == source_id), None)
    if not source:
        return {"ok": False, "error": f"Unknown source: {source_id}", "source_id": source_id}
    if source.get("kind") == "markdown_root":
        fragment = _markdown_graph_fragment(Path(resolve_source_root(source)), source, limit=limit_per_table)
        validation = validate_graph_fragment(fragment)
        return {
            "ok": validation["ok"],
            "source_id": source_id,
            "limit_per_table": limit_per_table,
            "fragment": fragment,
            "validation": validation,
        }
    if source.get("kind") == "kanban_project":
        fragment = _kanban_graph_fragment(Path(resolve_source_root(source)), source, limit=limit_per_table)
        validation = validate_graph_fragment(fragment)
        return {
            "ok": validation["ok"],
            "source_id": source_id,
            "limit_per_table": limit_per_table,
            "fragment": fragment,
            "validation": validation,
        }
    if source.get("kind") == "repo_root":
        fragment = _repo_graph_fragment(Path(resolve_source_root(source)), source, limit=limit_per_table)
        validation = validate_graph_fragment(fragment)
        return {
            "ok": validation["ok"],
            "source_id": source_id,
            "limit_per_table": limit_per_table,
            "fragment": fragment,
            "validation": validation,
        }
    if source.get("kind") == "hapa_ecosystem_codebases":
        is_full = full or limit_per_table <= 0
        effective_max_codebases = _ecosystem_sample_codebase_limit(
            full=is_full,
            limit_per_codebase=limit_per_table,
            max_codebases=max_codebases,
        )
        fragment_result = _hapa_ecosystem_codebases_fragment(
            source,
            limit_per_codebase=limit_per_table,
            full=is_full,
            max_codebases=effective_max_codebases,
        )
        fragment = fragment_result["fragment"]
        validation = validate_graph_fragment(fragment)
        return {
            "ok": validation["ok"] and fragment_result.get("ok", False),
            "source_id": source_id,
            "limit_per_table": limit_per_table,
            "full": is_full,
            "max_codebases": effective_max_codebases,
            "fragment": fragment,
            "validation": validation,
            "discovery": fragment_result.get("discovery"),
            "ast": fragment_result.get("ast"),
            "errors": fragment_result.get("errors", []),
        }
    if source.get("kind") != "sqlite":
        return {
            "ok": False,
            "error": f"Fragment builder currently supports sqlite, markdown_root, kanban_project, repo_root, and hapa_ecosystem_codebases sources only, got {source.get('kind')}",
            "source_id": source_id,
        }
    fragment = _sqlite_graph_fragment(Path(resolve_source_root(source)), source, limit_per_table=limit_per_table)
    validation = validate_graph_fragment(fragment)
    return {
        "ok": validation["ok"],
        "source_id": source_id,
        "limit_per_table": limit_per_table,
        "fragment": fragment,
        "validation": validation,
    }


def smoke(dry_run: bool = True) -> dict[str, Any]:
    steps = []

    def step(name: str, fn):
        started = time.perf_counter()
        try:
            data = fn()
            ok = bool(data.get("ok", True))
            error = None
        except Exception as exc:  # pragma: no cover - defensive smoke payload
            data = {}
            ok = False
            error = str(exc)
        steps.append({
            "name": name,
            "ok": ok,
            "data": data,
            "duration_seconds": round(time.perf_counter() - started, 4),
            "error": error,
        })

    step("health", lambda: health(deep=True))
    step("capabilities", capabilities)
    step("sources_validate", validate_sources)
    if dry_run:
        step("ingest_dry_run", lambda: ingest_dry_run("all"))
        step("second_brain_fragment_sample", lambda: {
            k: v for k, v in build_source_fragment("second-brain-live", limit_per_table=5).items()
            if k != "fragment"
        })
    return {
        "ok": all(item["ok"] for item in steps),
        "dry_run": dry_run,
        "run_id": f"hapa_graphify_smoke_{int(time.time())}",
        "steps_results": steps,
    }


def record_smoke_run(
    *,
    dry_run: bool = True,
    ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    report = smoke(dry_run=dry_run)
    ingest = ingest_dry_run("all")
    source_signatures = {
        summary["id"]: summary.get("source_signature")
        for summary in ingest.get("summaries", [])
        if summary.get("source_signature")
    }
    entry = {
        "run_id": report["run_id"],
        "ts": int(time.time()),
        "command": "smoke",
        "dry_run": dry_run,
        "ok": report["ok"],
        "graph_changed": False,
        "source_signatures": source_signatures,
        "summary": {
            "step_count": len(report["steps_results"]),
            "sources": ingest.get("source_count", 0),
        },
        "report": report,
    }
    append_ledger_entry(entry, ledger_path=ledger_path)
    return {
        "ok": report["ok"],
        "ledger_path": str(Path(ledger_path or DEFAULT_RUN_LEDGER)),
        "entry": entry,
    }


def append_ledger_entry(entry: dict[str, Any], *, ledger_path: str | Path | None = None) -> None:
    path = Path(ledger_path or DEFAULT_RUN_LEDGER)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")


def list_ledger_entries(*, ledger_path: str | Path | None = None, limit: int = 20) -> dict[str, Any]:
    path = Path(ledger_path or DEFAULT_RUN_LEDGER)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    if not path.exists():
        return {"ok": True, "ledger_path": str(path), "entries": []}
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"ok": False, "error": "unparseable ledger row"})
    return {"ok": True, "ledger_path": str(path), "entries": rows[-limit:]}


def append_since_last_success(
    *,
    dry_run: bool = True,
    ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    current = ingest_dry_run("all")
    current_signatures = {
        summary["id"]: summary.get("source_signature")
        for summary in current.get("summaries", [])
        if summary.get("source_signature")
    }
    previous = _latest_successful_source_signatures(ledger_path=ledger_path)
    delta = compute_signature_delta(previous, current_signatures)
    result = {
        "ok": current["ok"],
        "dry_run": dry_run,
        "run_id": f"hapa_graphify_append_{int(time.time())}",
        "since": "last-success",
        "graph_changed": False if dry_run else bool(delta["changed"] or delta["added"] or delta["removed"]),
        "delta": delta,
        "source_signatures": current_signatures,
        "tombstone_candidates": [
            {"source_id": source_id, "previous_signature": signature}
            for source_id, signature in delta["removed"].items()
        ],
    }
    if not dry_run:
        append_ledger_entry({
            "run_id": result["run_id"],
            "ts": int(time.time()),
            "command": "append",
            "dry_run": False,
            "ok": result["ok"],
            "graph_changed": result["graph_changed"],
            "source_signatures": current_signatures,
            "summary": {"delta": delta},
        }, ledger_path=ledger_path)
    return result


def review_suggestions_for_source(source_id: str, *, limit_per_table: int = 100) -> dict[str, Any]:
    fragment_result = build_source_fragment(source_id, limit_per_table=limit_per_table)
    if not fragment_result.get("ok") and "fragment" not in fragment_result:
        return fragment_result
    suggestions = suggest_review_cards(
        fragment_result["fragment"],
        validation=fragment_result.get("validation"),
    )
    return {
        "ok": True,
        "source_id": source_id,
        "limit_per_table": limit_per_table,
        "fragment_ok": fragment_result.get("ok"),
        "draft_only": True,
        "authorized_append_required": True,
        "suggestions": suggestions,
    }


def telemetry_probe(urls: list[str] | None = None, *, timeout_seconds: float = 1.5) -> dict[str, Any]:
    """Probe local Hapa HTTP endpoints without auth headers or token file reads."""
    urls = urls or ["http://127.0.0.1:8796/health"]
    source_id = "hapa-graphify-telemetry"
    record_owner = "hapa-graphify"
    privacy = "private-local"
    nodes: list[dict[str, Any]] = []
    probes: list[dict[str, Any]] = []

    for raw_url in urls:
        observed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        parsed = urllib.parse.urlparse(raw_url)
        display_url = _display_probe_url(parsed, raw_url)
        host = parsed.hostname or ""
        scheme = parsed.scheme.lower()
        status = "blocked"
        error = None
        http_status = None
        truth_status = "blocked"

        if scheme not in {"http", "https"}:
            error = "unsupported_scheme"
        elif not _is_loopback_host(host):
            error = "non_loopback_blocked"
        else:
            request = urllib.request.Request(
                raw_url,
                method="GET",
                headers={"User-Agent": "hapa-graphify-telemetry/0.1"},
            )
            try:
                with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                    http_status = int(response.getcode())
                    status = "ok" if 200 <= http_status <= 299 else "http_error"
                    truth_status = "verified_runtime" if status == "ok" else "blocked"
                    if status != "ok":
                        error = "http_error"
            except urllib.error.HTTPError as exc:
                http_status = int(exc.code)
                status = "auth_required" if http_status in {401, 403} else "http_error"
                error = status
            except (TimeoutError, OSError, urllib.error.URLError):
                status = "offline_or_unreachable"
                error = status

        node = {
            "id": stable_id(source_id, "endpoint", display_url, display_url),
            "label": display_url,
            "type": "endpoint",
            "truth_status": truth_status,
            "source_id": source_id,
            "record_owner": record_owner,
            "privacy": privacy,
            "record_type": "telemetry_endpoint",
            "record_key": display_url,
            "scheme": scheme,
            "host": host,
            "status": status,
            "http_status": http_status,
            "error": error,
            "observed_at": observed_at,
            "command": f"GET {display_url}",
            "token_files_read": False,
            "auth_headers_sent": False,
            "loopback_only": True,
        }
        nodes.append(node)
        probes.append({
            "url": display_url,
            "ok": status == "ok",
            "status": status,
            "http_status": http_status,
            "error": error,
            "observed_at": observed_at,
        })

    fragment = {
        "schema": "hapa.graph.fragment.v1",
        "source_id": source_id,
        "nodes": nodes,
        "edges": [],
        "metadata": {
            "loopback_only": True,
            "token_files_read": False,
            "auth_headers_sent": False,
            "timeout_seconds": timeout_seconds,
        },
    }
    validation = validate_graph_fragment(fragment)
    return {
        "ok": validation["ok"],
        "source_id": source_id,
        "probe_count": len(probes),
        "verified_runtime_count": sum(1 for probe in probes if probe["ok"]),
        "blocked_count": sum(1 for probe in probes if not probe["ok"]),
        "probes": probes,
        "fragment": fragment,
        "validation": validation,
    }


def build_combined_graph(
    source_id: str = "all",
    *,
    limit_per_source: int = 50,
    full: bool = False,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry or load_registry()
    selected = [
        source for source in registry.get("sources", [])
        if source_id == "all" or source.get("id") == source_id
    ]
    if not selected:
        return {"ok": False, "error": f"Unknown source: {source_id}", "source_id": source_id}

    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges_by_key: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    source_results = []
    errors = []
    for source in selected:
        result = build_source_fragment(
            str(source["id"]),
            limit_per_table=0 if full else limit_per_source,
            full=full,
            registry=registry,
        )
        source_results.append({
            "source_id": source["id"],
            "ok": result.get("ok"),
            "validation": result.get("validation"),
            "error": result.get("error"),
        })
        if not result.get("ok"):
            errors.append({"source_id": source["id"], "error": result.get("error"), "validation": result.get("validation")})
        fragment = result.get("fragment") or {}
        for node in fragment.get("nodes", []):
            nodes_by_id.setdefault(node["id"], node)
        for edge in fragment.get("edges", []):
            key = (
                str(edge.get("source")),
                str(edge.get("target")),
                str(edge.get("type")),
                str(edge.get("source_id")),
            )
            edges_by_key.setdefault(key, edge)

    fragment = {
        "schema": "hapa.graph.fragment.v1",
        "source_id": source_id,
        "nodes": list(nodes_by_id.values()),
        "edges": list(edges_by_key.values()),
        "metadata": {
            "source_count": len(selected),
            "limit_per_source": limit_per_source,
            "full": full,
            "source_results": source_results,
        },
    }
    validation = validate_graph_fragment(fragment)
    return {
        "ok": validation["ok"] and not errors,
        "source_id": source_id,
        "fragment": fragment,
        "validation": validation,
        "source_results": source_results,
        "errors": errors,
    }


def query_graph(
    query: str,
    *,
    source_id: str = "all",
    limit: int = 20,
    limit_per_source: int = 50,
    node_type: str | None = None,
    truth_status: str | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    combined = build_combined_graph(source_id, limit_per_source=limit_per_source, registry=registry)
    if not combined.get("ok"):
        return combined
    needle = query.strip().lower()
    matches = []
    for node in combined["fragment"]["nodes"]:
        if node_type and str(node.get("type") or "") != node_type:
            continue
        if truth_status and str(node.get("truth_status") or "") != truth_status:
            continue
        haystack = " ".join(
            str(node.get(field) or "")
            for field in ("id", "label", "type", "source_id", "record_type", "truth_status", "status", "article_type", "category")
        ).lower()
        if needle and needle not in haystack:
            continue
        label = str(node.get("label") or "")
        score = 3 if needle and label.lower() == needle else 2 if needle and needle in label.lower() else 1
        matches.append({"score": score, "node": _node_summary(node)})
    matches.sort(key=lambda item: (-item["score"], item["node"]["label"]))
    return {
        "ok": True,
        "query": query,
        "source_id": source_id,
        "limit": limit,
        "limit_per_source": limit_per_source,
        "node_type": node_type,
        "truth_status": truth_status,
        "match_count": len(matches),
        "matches": matches[:limit],
        "graph": _graph_summary(combined["fragment"]),
    }


def browse_graph_nodes(
    *,
    source_id: str,
    query: str = "",
    limit: int = 50,
    offset: int = 0,
    limit_per_source: int | None = None,
    node_type: str | None = None,
    truth_status: str | None = None,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sample_limit = limit_per_source if limit_per_source is not None else max(limit + offset, limit)
    combined = build_combined_graph(source_id, limit_per_source=sample_limit, registry=registry)
    if not combined.get("ok"):
        return combined
    needle = query.strip().lower()
    nodes = []
    for node in combined["fragment"].get("nodes", []):
        if node_type and str(node.get("type") or "") != node_type:
            continue
        if truth_status and str(node.get("truth_status") or "") != truth_status:
            continue
        if needle:
            haystack = " ".join(
                str(node.get(field) or "")
                for field in ("id", "label", "type", "source_id", "record_type", "truth_status", "status", "article_type", "category")
            ).lower()
            if needle not in haystack:
                continue
        nodes.append(_node_summary(node, include_details=True))
    return {
        "ok": True,
        "source_id": source_id,
        "query": query,
        "limit": limit,
        "offset": offset,
        "sample_limit": sample_limit,
        "filtered_count": len(nodes),
        "nodes": nodes[offset:offset + limit],
        "graph": _graph_summary(combined["fragment"]),
    }


def path_between(
    start: str,
    end: str,
    *,
    source_id: str = "all",
    max_depth: int = 6,
    limit_per_source: int = 50,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    combined = build_combined_graph(source_id, limit_per_source=limit_per_source, registry=registry)
    if not combined.get("ok"):
        return combined
    nodes = combined["fragment"]["nodes"]
    edges = combined["fragment"]["edges"]
    start_node = _find_node(nodes, start)
    end_node = _find_node(nodes, end)
    if not start_node or not end_node:
        return {
            "ok": True,
            "found": False,
            "reason": "start_or_end_not_found",
            "start": start,
            "end": end,
            "start_found": bool(start_node),
            "end_found": bool(end_node),
            "graph": _graph_summary(combined["fragment"]),
        }

    adjacency: dict[str, list[tuple[str, dict[str, Any], bool]]] = {}
    for edge in edges:
        src = str(edge.get("source"))
        tgt = str(edge.get("target"))
        adjacency.setdefault(src, []).append((tgt, edge, False))
        adjacency.setdefault(tgt, []).append((src, edge, True))

    queue: list[tuple[str, list[str], list[dict[str, Any]]]] = [(start_node["id"], [start_node["id"]], [])]
    seen = {start_node["id"]}
    node_lookup = {node["id"]: node for node in nodes}
    while queue:
        current, node_path, edge_path = queue.pop(0)
        if current == end_node["id"]:
            return {
                "ok": True,
                "found": True,
                "start": _node_summary(start_node),
                "end": _node_summary(end_node),
                "depth": len(edge_path),
                "nodes": [_node_summary(node_lookup[node_id]) for node_id in node_path],
                "edges": edge_path,
                "graph": _graph_summary(combined["fragment"]),
            }
        if len(edge_path) >= max_depth:
            continue
        for next_id, edge, reversed_edge in adjacency.get(current, []):
            if next_id in seen:
                continue
            seen.add(next_id)
            queue.append((
                next_id,
                [*node_path, next_id],
                [*edge_path, _edge_summary(edge, reversed_edge=reversed_edge)],
            ))

    return {
        "ok": True,
        "found": False,
        "reason": "no_path_within_max_depth",
        "start": _node_summary(start_node),
        "end": _node_summary(end_node),
        "max_depth": max_depth,
        "graph": _graph_summary(combined["fragment"]),
    }


def explain_graph_node(
    identifier: str,
    *,
    source_id: str = "all",
    limit_per_source: int = 50,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    combined = build_combined_graph(source_id, limit_per_source=limit_per_source, registry=registry)
    if not combined.get("ok"):
        return combined
    fragment = combined["fragment"]
    node = _find_node(fragment["nodes"], identifier)
    if not node:
        return {
            "ok": True,
            "found": False,
            "identifier": identifier,
            "graph": _graph_summary(fragment),
        }
    incoming = [edge for edge in fragment["edges"] if edge.get("target") == node["id"]]
    outgoing = [edge for edge in fragment["edges"] if edge.get("source") == node["id"]]
    return {
        "ok": True,
        "found": True,
        "node": _node_summary(node, include_details=True),
        "incoming_count": len(incoming),
        "outgoing_count": len(outgoing),
        "incoming": [_edge_summary(edge) for edge in incoming[:10]],
        "outgoing": [_edge_summary(edge) for edge in outgoing[:10]],
        "graph": _graph_summary(fragment),
    }


def reconcile_against(
    target: str = "second-brain",
    *,
    dry_run: bool = True,
    ledger_path: str | Path | None = None,
) -> dict[str, Any]:
    append_result = append_since_last_success(dry_run=True, ledger_path=ledger_path)
    delta = append_result.get("delta", {})
    return {
        "ok": append_result.get("ok", False),
        "target": target,
        "dry_run": dry_run,
        "run_id": f"hapa_graphify_reconcile_{int(time.time())}",
        "graph_changed": False if dry_run else append_result.get("graph_changed", False),
        "requires_authorized_write": not dry_run,
        "delta": delta,
        "conflict_count": len(delta.get("changed", {})) + len(delta.get("removed", {})),
        "tombstone_candidates": append_result.get("tombstone_candidates", []),
        "source_signatures": append_result.get("source_signatures", {}),
    }


def export_graph(
    *,
    source_id: str = "all",
    output: str | Path | None = None,
    dry_run: bool = True,
    public: bool = False,
    limit_per_source: int = 50,
    full: bool = False,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    registry = registry or load_registry()
    combined = build_combined_graph(source_id, limit_per_source=limit_per_source, full=full, registry=registry)
    if not combined.get("ok"):
        return combined
    output_path = Path(output) if output else DEFAULT_EXPORT_DIR / f"hapa-graphify-{source_id}-{int(time.time())}.json"
    if not output_path.is_absolute():
        output_path = (ROOT / output_path).resolve()
    graph = redact_public_fragment(combined["fragment"]) if public else combined["fragment"]
    validation = validate_graph_fragment(graph)
    payload = {
        "format": "hapa.graph.fragment.v1",
        "dry_run": dry_run,
        "public": public,
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "graph": graph,
        "validation": validation,
    }
    if not dry_run:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        append_ledger_entry({
            "run_id": f"hapa_graphify_export_{int(time.time())}",
            "ts": int(time.time()),
            "command": "export",
            "dry_run": False,
            "ok": True,
            "graph_changed": False,
            "source_signatures": {
                summary["id"]: summary.get("source_signature")
                for summary in ingest_dry_run("all", registry=registry).get("summaries", [])
                if summary.get("source_signature")
            },
            "summary": {"output": str(output_path), "public": public, **_graph_summary(graph)},
        })
    return {
        "ok": True,
        "dry_run": dry_run,
        "public": public,
        "source_id": source_id,
        "output": str(output_path),
        "would_write": dry_run,
        "wrote": not dry_run,
        "graph": _graph_summary(graph),
        "validation": validation,
    }


def report_summaries(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(reports_dir) if reports_dir else ROOT / "reports"
    if not root.is_absolute():
        root = (ROOT / root).resolve()
    summaries = []
    if root.exists():
        for path in sorted(root.glob("*.summary.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            output = Path(str(data.get("output") or ""))
            map_path = output.with_suffix(output.suffix + ".map.json") if output.suffix else None
            map_exists = bool(map_path and map_path.exists())
            summaries.append(data | {
                "summary_path": str(path),
                "summary_bytes": path.stat().st_size,
                "map_path": str(map_path) if map_exists else None,
                "map_exists": map_exists,
            })
    return {
        "ok": True,
        "reports_dir": str(root),
        "count": len(summaries),
        "summaries": summaries,
    }


def report_maps(*, reports_dir: str | Path | None = None) -> dict[str, Any]:
    root = Path(reports_dir) if reports_dir else ROOT / "reports"
    if not root.is_absolute():
        root = (ROOT / root).resolve()
    maps = []
    if root.exists():
        for path in sorted(root.glob("*.map.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            report = data.get("report", {})
            maps.append({
                "path": str(path),
                "bytes": path.stat().st_size,
                "schema": data.get("schema"),
                "kind": report.get("kind"),
                "run_id": report.get("run_id"),
                "graph": report.get("graph", {}),
                "available_levels": data.get("available_levels", []),
                "level_stats": data.get("level_stats", {}),
                "updated_at": report.get("updated_at"),
            })
    return {
        "ok": True,
        "reports_dir": str(root),
        "count": len(maps),
        "maps": maps,
    }


def graph_overview(
    *,
    kind: str = "all",
    level: str = "community",
    limit: int = 80,
    edge_limit: int = 220,
    reports_dir: str | Path | None = None,
) -> dict[str, Any]:
    maps_result = report_maps(reports_dir=reports_dir)
    maps = maps_result.get("maps", [])
    if kind not in {"", "all", "latest"}:
        maps = [item for item in maps if item.get("kind") == kind]
    maps = sorted(maps, key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    if not maps:
        return {
            "ok": True,
            "kind": kind,
            "level": level,
            "available_levels": [],
            "nodes": [],
            "edges": [],
            "graph": {"node_count": 0, "edge_count": 0},
            "maps": maps_result.get("maps", []),
            "message": "no map sidecars available; run or regenerate full report sidecars",
        }

    if kind in {"", "all"} and len(maps) > 1:
        return _combined_graph_overview(
            maps,
            requested_level=level,
            limit=limit,
            edge_limit=edge_limit,
            all_maps=maps_result.get("maps", []),
        )

    map_path = Path(str(maps[0]["path"]))
    data = json.loads(map_path.read_text(encoding="utf-8"))
    available_levels = data.get("available_levels") or list((data.get("levels") or {}).keys())
    selected_level = level if level in (data.get("levels") or {}) else (available_levels[0] if available_levels else level)
    level_data = (data.get("levels") or {}).get(selected_level, {"nodes": [], "edges": []})
    nodes = sorted(level_data.get("nodes", []), key=lambda node: (-int(node.get("node_count") or 0), str(node.get("label") or "")))
    if limit > 0:
        nodes = nodes[:limit]
    node_ids = {str(node.get("id")) for node in nodes}
    edges = [
        edge for edge in level_data.get("edges", [])
        if str(edge.get("source")) in node_ids and str(edge.get("target")) in node_ids
    ]
    edges.sort(key=lambda edge: (-int(edge.get("edge_count") or 0), str(edge.get("source") or ""), str(edge.get("target") or "")))
    if edge_limit > 0:
        edges = edges[:edge_limit]
    report = data.get("report", {})
    return {
        "ok": True,
        "kind": report.get("kind"),
        "level": selected_level,
        "requested_level": level,
        "available_levels": available_levels,
        "map_path": str(map_path),
        "report": report,
        "nodes": nodes,
        "edges": edges,
        "graph": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "full_node_count": report.get("graph", {}).get("node_count"),
            "full_edge_count": report.get("graph", {}).get("edge_count"),
        },
        "level_stats": data.get("level_stats", {}).get(selected_level, {}),
        "maps": maps_result.get("maps", []),
    }


def graph_group_neighbors(
    group_id: str,
    *,
    kind: str = "all",
    level: str = "source_type",
    limit: int = 24,
    edge_limit: int = 80,
    reports_dir: str | Path | None = None,
) -> dict[str, Any]:
    maps_result = report_maps(reports_dir=reports_dir)
    maps = maps_result.get("maps", [])
    if kind not in {"", "all", "latest"}:
        maps = [item for item in maps if item.get("kind") == kind]
    maps = sorted(maps, key=lambda item: str(item.get("updated_at") or ""), reverse=True)
    if not maps:
        return {"ok": False, "error": "no_map_sidecars_available", "group_id": group_id}

    selected = None
    for item in maps:
        candidate_path = Path(str(item["path"]))
        candidate_data = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate_levels = candidate_data.get("available_levels") or list((candidate_data.get("levels") or {}).keys())
        candidate_level = level if level in (candidate_data.get("levels") or {}) else (candidate_levels[0] if candidate_levels else level)
        candidate_level_data = (candidate_data.get("levels") or {}).get(candidate_level, {"nodes": [], "edges": []})
        if any(str(node.get("id")) == group_id for node in candidate_level_data.get("nodes", [])):
            selected = (candidate_path, candidate_data, candidate_levels, candidate_level, candidate_level_data)
            break

    if selected is None:
        map_path = Path(str(maps[0]["path"]))
        data = json.loads(map_path.read_text(encoding="utf-8"))
        available_levels = data.get("available_levels") or list((data.get("levels") or {}).keys())
        selected_level = level if level in (data.get("levels") or {}) else (available_levels[0] if available_levels else level)
        level_data = (data.get("levels") or {}).get(selected_level, {"nodes": [], "edges": []})
    else:
        map_path, data, available_levels, selected_level, level_data = selected

    nodes_by_id = {str(node.get("id")): node for node in level_data.get("nodes", [])}
    focus = nodes_by_id.get(group_id)
    if not focus:
        return {
            "ok": False,
            "error": "group_not_found",
            "group_id": group_id,
            "kind": kind,
            "level": selected_level,
            "available_levels": available_levels,
        }

    adjacent = [
        edge for edge in level_data.get("edges", [])
        if str(edge.get("source")) == group_id or str(edge.get("target")) == group_id
    ]
    adjacent.sort(key=lambda edge: (-int(edge.get("edge_count") or 0), str(edge.get("source") or ""), str(edge.get("target") or "")))
    neighbor_scores: dict[str, int] = {}
    for edge in adjacent:
        source = str(edge.get("source"))
        target = str(edge.get("target"))
        neighbor_id = target if source == group_id else source
        neighbor_scores[neighbor_id] = neighbor_scores.get(neighbor_id, 0) + int(edge.get("edge_count") or 0)
    neighbor_ids = [
        neighbor_id
        for neighbor_id, _score in sorted(neighbor_scores.items(), key=lambda item: (-item[1], str(nodes_by_id.get(item[0], {}).get("label") or item[0])))[:limit]
    ]
    included_ids = {group_id, *neighbor_ids}
    edges = [
        edge for edge in adjacent
        if str(edge.get("source")) in included_ids and str(edge.get("target")) in included_ids
    ]
    if edge_limit > 0:
        edges = edges[:edge_limit]

    focus_node = dict(focus)
    focus_node["focus"] = True
    neighbor_nodes = [nodes_by_id[neighbor_id] for neighbor_id in neighbor_ids if neighbor_id in nodes_by_id]
    report = data.get("report", {})
    return {
        "ok": True,
        "kind": report.get("kind"),
        "level": selected_level,
        "requested_level": level,
        "group_id": group_id,
        "focus": focus_node,
        "nodes": [focus_node, *neighbor_nodes],
        "edges": edges,
        "neighbor_count": len(neighbor_scores),
        "visible_neighbor_count": len(neighbor_nodes),
        "map_path": str(map_path),
        "report": report,
        "graph": {
            "node_count": 1 + len(neighbor_nodes),
            "edge_count": len(edges),
            "full_node_count": report.get("graph", {}).get("node_count"),
            "full_edge_count": report.get("graph", {}).get("edge_count"),
        },
    }


def _combined_graph_overview(
    maps: list[dict[str, Any]],
    *,
    requested_level: str,
    limit: int,
    edge_limit: int,
    all_maps: list[dict[str, Any]],
) -> dict[str, Any]:
    loaded_maps = []
    available_levels = set()
    for item in maps:
        data = json.loads(Path(str(item["path"])).read_text(encoding="utf-8"))
        loaded_maps.append(data)
        available_levels.update(data.get("available_levels") or list((data.get("levels") or {}).keys()))
    selected_level = requested_level if requested_level in available_levels else sorted(available_levels)[0]

    combined_nodes: dict[str, dict[str, Any]] = {}
    combined_edges: dict[tuple[str, str], dict[str, Any]] = {}
    full_node_count = 0
    full_edge_count = 0
    report_refs = []
    for data in loaded_maps:
        report = data.get("report", {})
        report_refs.append({
            "kind": report.get("kind"),
            "run_id": report.get("run_id"),
            "graph": report.get("graph", {}),
        })
        full_node_count += int(report.get("graph", {}).get("node_count") or 0)
        full_edge_count += int(report.get("graph", {}).get("edge_count") or 0)
        level_data = (data.get("levels") or {}).get(selected_level, {"nodes": [], "edges": []})
        for node in level_data.get("nodes", []):
            _merge_map_group(combined_nodes, node, report.get("kind"))
        for edge in level_data.get("edges", []):
            _merge_map_edge(combined_edges, edge)

    nodes = sorted(combined_nodes.values(), key=lambda node: (-int(node.get("node_count") or 0), str(node.get("label") or "")))
    if limit > 0:
        nodes = nodes[:limit]
    node_ids = {str(node.get("id")) for node in nodes}
    edges = [
        edge for edge in combined_edges.values()
        if str(edge.get("source")) in node_ids and str(edge.get("target")) in node_ids
    ]
    edges.sort(key=lambda edge: (-int(edge.get("edge_count") or 0), str(edge.get("source") or ""), str(edge.get("target") or "")))
    if edge_limit > 0:
        edges = edges[:edge_limit]

    return {
        "ok": True,
        "kind": "all",
        "level": selected_level,
        "requested_level": requested_level,
        "available_levels": sorted(available_levels),
        "map_path": None,
        "report": {
            "kind": "all",
            "run_id": "combined-all",
            "graph": {
                "node_count": full_node_count,
                "edge_count": full_edge_count,
            },
            "reports": report_refs,
        },
        "nodes": nodes,
        "edges": edges,
        "graph": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "full_node_count": full_node_count,
            "full_edge_count": full_edge_count,
        },
        "level_stats": {
            "node_count": len(combined_nodes),
            "edge_count": len(combined_edges),
            "report_count": len(loaded_maps),
        },
        "maps": all_maps,
    }


def _merge_map_group(groups: dict[str, dict[str, Any]], node: dict[str, Any], kind: str | None) -> None:
    group = groups.setdefault(str(node.get("id")), {
        **node,
        "node_count": 0,
        "edge_count": 0,
        "internal_edge_count": 0,
        "external_edge_count": 0,
        "source_counts": [],
        "type_counts": [],
        "truth_counts": [],
        "owner_counts": [],
        "samples": [],
        "report_kinds": [],
    })
    for key in ("node_count", "edge_count", "internal_edge_count", "external_edge_count"):
        group[key] = int(group.get(key) or 0) + int(node.get(key) or 0)
    for key in ("source_counts", "type_counts", "truth_counts", "owner_counts"):
        group[key] = _merge_count_lists(group.get(key, []), node.get(key, []))
    samples = list(group.get("samples", []))
    seen_samples = {str(sample.get("id")) for sample in samples}
    for sample in node.get("samples", []):
        if len(samples) >= MAP_GROUP_SAMPLE_SIZE:
            break
        if str(sample.get("id")) in seen_samples:
            continue
        samples.append(sample)
        seen_samples.add(str(sample.get("id")))
    group["samples"] = samples
    if kind and kind not in group["report_kinds"]:
        group["report_kinds"].append(kind)


def _merge_map_edge(edges: dict[tuple[str, str], dict[str, Any]], edge: dict[str, Any]) -> None:
    key = (str(edge.get("source")), str(edge.get("target")))
    merged = edges.setdefault(key, {
        **edge,
        "edge_count": 0,
        "edge_type_counts": [],
        "truth_counts": [],
    })
    merged["edge_count"] = int(merged.get("edge_count") or 0) + int(edge.get("edge_count") or 0)
    merged["edge_type_counts"] = _merge_count_lists(merged.get("edge_type_counts", []), edge.get("edge_type_counts", []))
    merged["truth_counts"] = _merge_count_lists(merged.get("truth_counts", []), edge.get("truth_counts", []))


def _merge_count_lists(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for item in [*left, *right]:
        counts[str(item.get("key") or "unknown")] = counts.get(str(item.get("key") or "unknown"), 0) + int(item.get("count") or 0)
    return _top_counts(counts)


def write_report_sidecars_for_output(output_path: str | Path) -> dict[str, Any]:
    path = Path(output_path)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    data = json.loads(path.read_text(encoding="utf-8"))
    report = data.get("report") if isinstance(data.get("report"), dict) else data
    fragment = data.get("graph") if isinstance(data.get("graph"), dict) else None
    _write_report_summary(path, report, fragment)
    return {
        "ok": True,
        "output": str(path),
        "summary_path": str(path.with_suffix(path.suffix + ".summary.json")),
        "map_path": str(path.with_suffix(path.suffix + ".map.json")) if fragment else None,
        "mapped": bool(fragment),
    }


def _write_report_summary(output_path: Path, report: dict[str, Any], fragment: dict[str, Any] | None = None) -> None:
    summary = _report_summary_from_report(output_path, report)
    summary_path = output_path.with_suffix(output_path.suffix + ".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    if fragment:
        _write_report_map(output_path, report, fragment, summary)


def _report_summary_from_report(output_path: Path, report: dict[str, Any]) -> dict[str, Any]:
    source_summaries = []
    for source in report.get("sources") or []:
        validation = source.get("validation") if isinstance(source.get("validation"), dict) else {}
        metadata = source.get("metadata") if isinstance(source.get("metadata"), dict) else {}
        source_summaries.append({
            "source_id": source.get("source_id"),
            "ok": source.get("ok"),
            "node_count": validation.get("node_count"),
            "edge_count": validation.get("edge_count"),
            "metadata": {
                key: value
                for key, value in metadata.items()
                if key in {
                    "full",
                    "limit",
                    "limit_per_table",
                    "markdown_pages_available",
                    "markdown_pages_selected",
                    "directory_nodes",
                    "heading_nodes",
                    "wikilink_edges",
                    "codebase_count",
                    "selected_code_files",
                    "total_code_files",
                    "event_count_sampled",
                    "project_id",
                }
            },
        })
    ast = report.get("ast") if isinstance(report.get("ast"), dict) else {}
    discovery = report.get("discovery") if isinstance(report.get("discovery"), dict) else {}
    return {
        "ok": report.get("ok"),
        "run_id": report.get("run_id"),
        "full": report.get("full"),
        "graph": report.get("graph", {}),
        "validation": {
            "ok": report.get("validation", {}).get("ok") if isinstance(report.get("validation"), dict) else None,
            "node_count": report.get("validation", {}).get("node_count") if isinstance(report.get("validation"), dict) else None,
            "edge_count": report.get("validation", {}).get("edge_count") if isinstance(report.get("validation"), dict) else None,
            "error_count": len(report.get("validation", {}).get("errors", [])) if isinstance(report.get("validation"), dict) else None,
        },
        "error_count": len(report.get("errors") or []),
        "output": str(output_path),
        "output_bytes": output_path.stat().st_size if output_path.exists() else None,
        "kind": _report_kind(output_path, report),
        "sources": source_summaries,
        "ast": {
            "available": ast.get("available"),
            "codebase_count": ast.get("codebase_count"),
            "total_code_files": ast.get("total_code_files"),
            "selected_code_files": ast.get("selected_code_files"),
        } if ast else None,
        "discovery": {
            "node_root_count": discovery.get("node_root_count"),
            "codebase_count": discovery.get("codebase_count"),
            "missing_count": discovery.get("missing_count"),
        } if discovery else None,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(output_path.stat().st_mtime)) if output_path.exists() else None,
    }


def _report_kind(output_path: Path, report: dict[str, Any]) -> str:
    text = f"{output_path.name} {report.get('run_id', '')}".lower()
    if "knowledge" in text:
        return "knowledge"
    if "ecosystem" in text or "ast" in text:
        return "code_ast"
    return "graph"


def _write_report_map(output_path: Path, report: dict[str, Any], fragment: dict[str, Any], summary: dict[str, Any]) -> None:
    atlas = _build_report_map(output_path, report, fragment, summary)
    map_path = output_path.with_suffix(output_path.suffix + ".map.json")
    map_path.write_text(json.dumps(atlas, indent=2, sort_keys=True), encoding="utf-8")


def _build_report_map(
    output_path: Path,
    report: dict[str, Any],
    fragment: dict[str, Any],
    summary: dict[str, Any],
) -> dict[str, Any]:
    levels = {
        level: _aggregate_map_level(level, fragment.get("nodes", []), fragment.get("edges", []))
        for level in MAP_LEVELS
    }
    return {
        "schema": "hapa.graph.map.v1",
        "report": {
            "run_id": report.get("run_id"),
            "kind": _report_kind(output_path, report),
            "ok": report.get("ok"),
            "full": report.get("full"),
            "graph": report.get("graph", {}),
            "output": str(output_path),
            "output_bytes": summary.get("output_bytes"),
            "updated_at": summary.get("updated_at"),
        },
        "available_levels": list(levels.keys()),
        "level_stats": {
            level: {
                "node_count": len(data.get("nodes", [])),
                "edge_count": len(data.get("edges", [])),
            }
            for level, data in levels.items()
        },
        "levels": levels,
    }


def _aggregate_map_level(level: str, nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[str, dict[str, Any]] = {}
    node_to_group: dict[str, str] = {}

    for node in nodes:
        group_key, label, attributes = _map_group_key(level, node)
        group_id = _map_group_id(level, group_key)
        node_to_group[str(node.get("id"))] = group_id
        group = groups.setdefault(group_id, {
            "id": group_id,
            "label": label,
            "level": level,
            "key": group_key,
            "type": "map_group",
            "group_type": level,
            "node_count": 0,
            "edge_count": 0,
            "internal_edge_count": 0,
            "external_edge_count": 0,
            "source_counts": {},
            "type_counts": {},
            "truth_counts": {},
            "owner_counts": {},
            "samples": [],
            **attributes,
        })
        group["node_count"] += 1
        _increment_count(group["source_counts"], str(node.get("source_id") or "unknown"))
        _increment_count(group["type_counts"], str(node.get("type") or "unknown"))
        _increment_count(group["truth_counts"], str(node.get("truth_status") or "unknown"))
        _increment_count(group["owner_counts"], str(node.get("record_owner") or "unknown"))
        if len(group["samples"]) < MAP_GROUP_SAMPLE_SIZE:
            group["samples"].append(_map_node_sample(node))

    grouped_edges: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in edges:
        source_group = node_to_group.get(str(edge.get("source", edge.get("from"))))
        target_group = node_to_group.get(str(edge.get("target", edge.get("to"))))
        if not source_group or not target_group:
            continue
        edge_type = str(edge.get("type", edge.get("relation")) or "relates_to")
        if source_group == target_group:
            groups[source_group]["internal_edge_count"] += 1
            groups[source_group]["edge_count"] += 1
            continue
        key = (source_group, target_group)
        grouped = grouped_edges.setdefault(key, {
            "id": _map_edge_id(level, source_group, target_group),
            "source": source_group,
            "target": target_group,
            "type": "aggregated",
            "edge_count": 0,
            "edge_type_counts": {},
            "truth_counts": {},
        })
        grouped["edge_count"] += 1
        _increment_count(grouped["edge_type_counts"], edge_type)
        _increment_count(grouped["truth_counts"], str(edge.get("truth_status") or "unknown"))
        groups[source_group]["edge_count"] += 1
        groups[target_group]["edge_count"] += 1
        groups[source_group]["external_edge_count"] += 1
        groups[target_group]["external_edge_count"] += 1

    return {
        "nodes": [_finalize_map_group(group) for group in groups.values()],
        "edges": [_finalize_map_edge(edge) for edge in grouped_edges.values()],
    }


def _map_group_key(level: str, node: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    source_id = str(node.get("source_id") or "unknown")
    node_type = str(node.get("type") or "unknown")
    truth_status = str(node.get("truth_status") or "unknown")
    owner = str(node.get("record_owner") or "unknown")
    if level == "community":
        return source_id, source_id, {"source_id": source_id, "community": source_id}
    if level == "type":
        return node_type, node_type, {"node_type": node_type}
    if level == "source_type":
        key = f"{source_id}::{node_type}"
        return key, f"{source_id} / {node_type}", {"source_id": source_id, "node_type": node_type}
    if level == "truth":
        return truth_status, truth_status, {"truth_status": truth_status}
    if level == "owner":
        return owner, owner, {"record_owner": owner}
    return source_id, source_id, {"source_id": source_id}


def _map_group_id(level: str, key: str) -> str:
    digest = hashlib.sha1(f"{level}:{key}".encode("utf-8")).hexdigest()[:12]
    return f"map:{level}:{digest}"


def _map_edge_id(level: str, source_group: str, target_group: str) -> str:
    digest = hashlib.sha1(f"{level}:{source_group}->{target_group}".encode("utf-8")).hexdigest()[:12]
    return f"map-edge:{level}:{digest}"


def _map_node_sample(node: dict[str, Any]) -> dict[str, Any]:
    sample = _node_summary(node)
    for key in ("record_key", "article_type", "category", "status", "node_kind"):
        if node.get(key) is not None:
            sample[key] = node.get(key)
    return sample


def _increment_count(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1


def _top_counts(counter: dict[str, int], limit: int = 8) -> list[dict[str, Any]]:
    return [
        {"key": key, "count": count}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _finalize_map_group(group: dict[str, Any]) -> dict[str, Any]:
    output = dict(group)
    output["source_counts"] = _top_counts(output.get("source_counts", {}))
    output["type_counts"] = _top_counts(output.get("type_counts", {}))
    output["truth_counts"] = _top_counts(output.get("truth_counts", {}))
    output["owner_counts"] = _top_counts(output.get("owner_counts", {}))
    return output


def _finalize_map_edge(edge: dict[str, Any]) -> dict[str, Any]:
    output = dict(edge)
    output["edge_type_counts"] = _top_counts(output.get("edge_type_counts", {}))
    output["truth_counts"] = _top_counts(output.get("truth_counts", {}))
    return output


def board_checkpoint(
    message: str,
    *,
    dry_run: bool = True,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "id": f"evt_{int(time.time() * 1000)}_{hashlib.sha1(message.encode('utf-8')).hexdigest()[:8]}",
        "project_id": "hapa-app-hapa-graphify",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "actor": "hapa-graphify",
        "type": "checkpoint",
        "task_id": None,
        "parent_event_id": None,
        "visibility": "project",
        "protocol": {
            "truthStatus": "verified_runtime",
            "recordOwner": "hapa-overwatch-kanban",
            "source": "hapa-graphify-cli",
        },
        "links": [
            {"label": "Hapa Graphify CLI", "href": str(ROOT)},
        ],
        "payload": {
            "title": "Hapa Graphify CLI checkpoint",
            "summary": message,
            "dry_run": dry_run,
        },
    }
    event_log = _board_event_log_path(registry or load_registry())
    if not dry_run:
        if not event_log:
            return {"ok": False, "dry_run": dry_run, "error": "board_event_log_not_found", "event": event}
        event_log.parent.mkdir(parents=True, exist_ok=True)
        with event_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
    return {
        "ok": True,
        "dry_run": dry_run,
        "would_append": dry_run,
        "appended": not dry_run,
        "event_log": str(event_log) if event_log else None,
        "event": event,
    }


def compute_signature_delta(previous: dict[str, str], current: dict[str, str]) -> dict[str, dict[str, Any]]:
    added = {key: current[key] for key in sorted(current) if key not in previous}
    removed = {key: previous[key] for key in sorted(previous) if key not in current}
    changed = {
        key: {"previous": previous[key], "current": current[key]}
        for key in sorted(current)
        if key in previous and previous[key] != current[key]
    }
    unchanged = {key: current[key] for key in sorted(current) if key in previous and previous[key] == current[key]}
    return {
        "added": added,
        "changed": changed,
        "removed": removed,
        "unchanged": unchanged,
    }


def _latest_successful_source_signatures(*, ledger_path: str | Path | None = None) -> dict[str, str]:
    entries = list_ledger_entries(ledger_path=ledger_path, limit=1000).get("entries", [])
    for entry in reversed(entries):
        if entry.get("ok") and isinstance(entry.get("source_signatures"), dict):
            return entry["source_signatures"]
    return {}


def _is_loopback_host(host: str) -> bool:
    return host.lower() in {"localhost", "127.0.0.1", "::1"}


def is_credential_path(path: str | Path) -> bool:
    text = str(path).replace("\\", "/")
    name = Path(text).name
    lowered = text.lower()
    return (
        name in {".env", ".node_token"}
        or lowered.endswith(".db-wal")
        or lowered.endswith(".db-shm")
        or "/.git/" in lowered
        or "/node_modules/" in lowered
        or "/tmp/" in lowered
        or lowered.startswith("tmp/")
        or "/public/generated/" in lowered
        or lowered.startswith("public/generated/")
        or "/raw/" in lowered
        or lowered.startswith("raw/")
        or "/private/" in lowered
        or lowered.startswith("private/")
        or "token" in name.lower()
        or "secret" in name.lower()
    )


def redact_public_fragment(fragment: dict[str, Any]) -> dict[str, Any]:
    redactions: list[dict[str, str]] = []

    def redact(value: Any, path: str) -> Any:
        if isinstance(value, dict):
            return {key: redact(item, f"{path}.{key}") for key, item in value.items()}
        if isinstance(value, list):
            return [redact(item, f"{path}[{index}]") for index, item in enumerate(value)]
        if isinstance(value, str):
            redacted = _redact_private_string(value)
            if redacted != value:
                redactions.append({"path": path, "reason": "private_local_path"})
            return redacted
        return value

    output = redact(fragment, "fragment")
    if isinstance(output, dict):
        metadata = output.setdefault("metadata", {})
        if isinstance(metadata, dict):
            metadata["public_redacted"] = True
            metadata["redaction_count"] = len(redactions)
            metadata["redactions"] = redactions[:100]
    return output


def _graph_summary(fragment: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": fragment.get("schema"),
        "source_id": fragment.get("source_id"),
        "node_count": len(fragment.get("nodes", [])),
        "edge_count": len(fragment.get("edges", [])),
    }


def _node_summary(node: dict[str, Any], *, include_details: bool = False) -> dict[str, Any]:
    summary = {
        "id": node.get("id"),
        "label": node.get("label"),
        "type": node.get("type"),
        "truth_status": node.get("truth_status"),
        "source_id": node.get("source_id"),
        "record_owner": node.get("record_owner"),
        "privacy": node.get("privacy"),
        "record_type": node.get("record_type"),
    }
    if include_details:
        summary["details"] = {
            key: value for key, value in node.items()
            if key not in summary and key not in {"source_file"}
        }
        if node.get("source_file"):
            summary["source_file"] = node.get("source_file")
    return summary


def _edge_summary(edge: dict[str, Any], *, reversed_edge: bool = False) -> dict[str, Any]:
    return {
        "source": edge.get("source"),
        "target": edge.get("target"),
        "type": edge.get("type"),
        "relation": edge.get("relation"),
        "truth_status": edge.get("truth_status"),
        "source_id": edge.get("source_id"),
        "reversed": reversed_edge,
    }


def _find_node(nodes: list[dict[str, Any]], identifier: str) -> dict[str, Any] | None:
    needle = identifier.strip().lower()
    for node in nodes:
        if str(node.get("id", "")).lower() == needle:
            return node
    for node in nodes:
        if str(node.get("label", "")).lower() == needle:
            return node
    for node in nodes:
        if needle and needle in str(node.get("label", "")).lower():
            return node
    return None


def _board_event_log_path(registry: dict[str, Any]) -> Path | None:
    for source in registry.get("sources", []):
        if source.get("kind") != "kanban_project":
            continue
        if source.get("project_id") != "hapa-app-hapa-graphify":
            continue
        root = Path(resolve_source_root(source))
        return root / "data" / "hapa-app-hapa-graphify" / "events.ndjson"
    return None


def _display_probe_url(parsed: urllib.parse.ParseResult, raw_url: str) -> str:
    if not parsed.scheme or not parsed.hostname:
        return raw_url.split("?", 1)[0].split("#", 1)[0]
    host = parsed.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    netloc = f"{host}:{parsed.port}" if parsed.port else host
    path = parsed.path or "/"
    return urllib.parse.urlunparse((parsed.scheme.lower(), netloc, path, "", "", ""))


def resolve_source_root(source: dict[str, Any]) -> str:
    root = _resolve_hapa_path(source.get("root", ""), base=ROOT)
    return str(root or ROOT)


def _validate_sqlite_source(root: Path, source: dict[str, Any]) -> dict[str, Any]:
    uri = f"file:{root}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as db:
            rows = db.execute(
                "select name from sqlite_master where type in ('table','view')"
            ).fetchall()
        available = {row[0] for row in rows}
        requested = set(source.get("include", []))
        missing = sorted(requested - available)
        return {"ok": not missing, "missing_tables": missing, "available_count": len(available)}
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}


def _summarize_source(source: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    root = Path(resolve_source_root(source))
    base = {
        "id": source.get("id"),
        "kind": source.get("kind"),
        "root": str(root),
        "ok": root.exists(),
        "privacy": source.get("privacy", registry.get("default_privacy")),
        "authority": source.get("authority", registry.get("default_authority")),
        "record_owner": source.get("record_owner"),
    }
    if not root.exists():
        return base | {"error": "root_missing"}
    if source.get("kind") == "sqlite":
        return base | _summarize_sqlite(root, source)
    if source.get("kind") == "kanban_project":
        return base | _summarize_kanban(root, source)
    if source.get("kind") == "hapa_ecosystem_codebases":
        return base | _summarize_hapa_ecosystem_codebases(source)
    if source.get("kind") in {"repo_root", "markdown_root"}:
        return base | _summarize_files(root, source, registry)
    return base | {"warning": "unknown_kind"}


def _summarize_sqlite(root: Path, source: dict[str, Any]) -> dict[str, Any]:
    uri = f"file:{root}?mode=ro"
    counts: dict[str, int] = {}
    try:
        with sqlite3.connect(uri, uri=True) as db:
            for table in source.get("include", []):
                if not _safe_sql_identifier(table):
                    continue
                try:
                    counts[table] = int(db.execute(f'select count(*) from "{table}"').fetchone()[0])
                except sqlite3.Error:
                    counts[table] = -1
        return {
            "row_counts": counts,
            "source_signature": _file_signature(root),
            "estimated_nodes": sum(v for v in counts.values() if v > 0),
        }
    except sqlite3.Error as exc:
        return {"ok": False, "error": str(exc)}


def _summarize_hapa_ecosystem_codebases(source: dict[str, Any]) -> dict[str, Any]:
    discovery_config = source.get("discovery") if isinstance(source.get("discovery"), dict) else {}
    discovery = discover_hapa_codebases(
        node_map_path=discovery_config.get("node_map"),
        quest_audit_path=discovery_config.get("quest_keeper_audit"),
        overwatch_config_dir=discovery_config.get("overwatch_config_dir"),
        manifest_scan_roots=discovery_config.get("manifest_scan_roots"),
    )
    sampled_codebases = [
        {
            "node_id": codebase.get("node_id"),
            "path": codebase.get("path"),
            "root_kind": codebase.get("root_kind"),
            "marker_files": codebase.get("marker_files", []),
        }
        for codebase in discovery["codebases"][:10]
    ]
    signature_paths = [
        Path(discovery["sources"]["node_map"]),
        Path(discovery["sources"]["quest_audit"]),
    ]
    config_dir = Path(discovery["sources"]["overwatch_config_dir"])
    if config_dir.exists():
        signature_paths.extend(sorted(config_dir.glob("*.json"))[:1000])
    return {
        "node_root_count": discovery["node_root_count"],
        "codebase_count": discovery["codebase_count"],
        "missing_count": discovery["missing_count"],
        "sample": sampled_codebases,
        "code_file_count_mode": "deferred_to_ecosystem_ast",
        "source_signature": _multi_file_signature([path for path in signature_paths if path.exists()]),
        "graphify_ast": _graphify_ast_status(),
    }


def _sqlite_graph_fragment(root: Path, source: dict[str, Any], *, limit_per_table: int) -> dict[str, Any]:
    uri = f"file:{root}?mode=ro"
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str, str, str]] = set()
    source_id = str(source["id"])
    record_owner = str(source.get("record_owner") or source_id)
    privacy = str(source.get("privacy") or "private-local")

    def add_node(node: dict[str, Any]) -> str:
        node_id = node["id"]
        if node_id not in seen_nodes:
            nodes.append(node)
            seen_nodes.add(node_id)
        return node_id

    def add_edge(edge: dict[str, Any]) -> None:
        key = (
            str(edge.get("source")),
            str(edge.get("target")),
            str(edge.get("type")),
            str(edge.get("source_id")),
            str(edge.get("relation", "")),
        )
        if key not in seen_edges and edge.get("source") != edge.get("target"):
            edges.append(edge)
            seen_edges.add(key)

    def base_node(record_type: str, key: str, label: str, node_type: str, truth_status: str = "verified_source", **extra: Any) -> dict[str, Any]:
        return {
            "id": stable_id(source_id, record_type, key, label),
            "label": label,
            "type": node_type,
            "truth_status": truth_status,
            "source_id": source_id,
            "record_owner": record_owner,
            "privacy": privacy,
            "record_type": record_type,
            "record_key": key,
            **extra,
        }

    with sqlite3.connect(uri, uri=True) as db:
        db.row_factory = sqlite3.Row
        available = _sqlite_table_names(db)

        if "hapa_nodes" in source.get("include", []) and "hapa_nodes" in available:
            for row in _sqlite_limited_rows(db, "select node_id, label, node_type, description from hapa_nodes", limit_per_table):
                add_node(base_node(
                    "hapa_node",
                    row["node_id"],
                    row["label"],
                    "hapa_node",
                    node_kind=row["node_type"],
                    description=row["description"],
                ))

        if "hapa_node_skills" in source.get("include", []) and "hapa_node_skills" in available:
            for row in _sqlite_limited_rows(db, "select node_skill_id, node_id, label, mode, description from hapa_node_skills", limit_per_table):
                capability = add_node(base_node(
                    "hapa_node_skill",
                    row["node_skill_id"],
                    row["label"],
                    "capability",
                    mode=row["mode"],
                    description=row["description"],
                ))
                node_label = row["node_id"]
                node_id = add_node(base_node("hapa_node", row["node_id"], node_label, "hapa_node"))
                add_edge(_edge(node_id, capability, "implements", source_id, record_owner, privacy, "verified_source"))

        if "skill_inventory" in source.get("include", []) and "skill_inventory" in available:
            for row in _sqlite_limited_rows(db, "select skill_id, label, skill_family, summary from skill_inventory", limit_per_table):
                add_node(base_node(
                    "skill",
                    row["skill_id"],
                    row["label"],
                    "skill",
                    skill_family=row["skill_family"],
                    summary=row["summary"],
                ))

        if "wiki_articles" in source.get("include", []) and "wiki_articles" in available:
            for row in _sqlite_limited_rows(db, "select article_id, slug, title, article_type, summary, body_md from wiki_articles", limit_per_table):
                article = add_node(base_node(
                    "wiki_article",
                    row["article_id"],
                    row["title"],
                    "wiki_article",
                    slug=row["slug"],
                    article_type=row["article_type"],
                    summary=row["summary"],
                ))
                for target in _wikilinks(row["body_md"] or "")[:20]:
                    concept = add_node(base_node(
                        "wikilink_target",
                        target,
                        target,
                        "concept",
                        "derived_or_inferred",
                    ))
                    add_edge(_edge(article, concept, "mentions", source_id, record_owner, privacy, "derived_or_inferred"))

        if "topics" in source.get("include", []) and "topics" in available:
            for row in _sqlite_limited_rows(db, "select topic_id, label, topic_type, description from topics", limit_per_table):
                add_node(base_node(
                    "topic",
                    row["topic_id"],
                    row["label"],
                    "concept",
                    "derived_or_inferred",
                    topic_type=row["topic_type"],
                    description=row["description"],
                ))

        if "knowledge_bodies" in source.get("include", []) and "knowledge_bodies" in available:
            for row in _sqlite_limited_rows(db, "select body_id, label, body_type, score, source_count, item_count, evidence_count, description from knowledge_bodies", limit_per_table):
                add_node(base_node(
                    "knowledge_body",
                    row["body_id"],
                    row["label"],
                    "wiki_article",
                    "derived_or_inferred",
                    body_type=row["body_type"],
                    score=row["score"],
                    source_count=row["source_count"],
                    item_count=row["item_count"],
                    evidence_count=row["evidence_count"],
                    description=row["description"],
                ))

        if "hapa_turn_cards" in source.get("include", []) and "hapa_turn_cards" in available:
            for row in _sqlite_limited_rows(db, "select card_id, turn_id, title, card_type from hapa_turn_cards", limit_per_table):
                card = add_node(base_node(
                    "turn_card",
                    row["card_id"],
                    row["title"],
                    "turn_card",
                    card_type=row["card_type"],
                ))
                turn = add_node(base_node("ai_chat_turn", row["turn_id"], row["turn_id"], "artifact"))
                add_edge(_edge(card, turn, "derived_from", source_id, record_owner, privacy, "verified_source"))

        if "ai_chat_turns" in source.get("include", []) and "ai_chat_turns" in available:
            for row in _sqlite_limited_rows(
                db,
                "select turn_id, thread_id, platform, turn_index, model_slug, objective, turn_type, topic_labels_json, knowledge_labels_json, decision_summary, work_summary, reusable_insight, hapa_relevance_score from ai_chat_turns",
                limit_per_table,
            ):
                turn = add_node(base_node(
                    "ai_chat_turn",
                    row["turn_id"],
                    row["objective"] or row["turn_id"],
                    "artifact",
                    platform=row["platform"],
                    turn_index=row["turn_index"],
                    model_slug=row["model_slug"],
                    turn_type=row["turn_type"],
                    topic_labels=row["topic_labels_json"],
                    knowledge_labels=row["knowledge_labels_json"],
                    decision_summary=row["decision_summary"],
                    work_summary=row["work_summary"],
                    reusable_insight=row["reusable_insight"],
                    hapa_relevance_score=row["hapa_relevance_score"],
                ))
                thread = add_node(base_node("ai_chat_thread", row["thread_id"], row["thread_id"], "artifact", platform=row["platform"]))
                add_edge(_edge(thread, turn, "indexes", source_id, record_owner, privacy, "verified_source"))

        if "ecosystem_connections" in source.get("include", []) and "ecosystem_connections" in available:
            for row in _sqlite_limited_rows(
                db,
                "select connection_id, subject_type, subject_id, subject_label, object_type, object_id, object_label, relation_type, score from ecosystem_connections",
                limit_per_table,
            ):
                subject = add_node(base_node(
                    str(row["subject_type"]),
                    row["subject_id"],
                    row["subject_label"],
                    _subject_type_to_node_type(row["subject_type"]),
                    "derived_or_inferred",
                ))
                obj = add_node(base_node(
                    str(row["object_type"]),
                    row["object_id"],
                    row["object_label"],
                    _subject_type_to_node_type(row["object_type"]),
                    "derived_or_inferred",
                ))
                add_edge(_edge(
                    subject,
                    obj,
                    "relates_to",
                    source_id,
                    record_owner,
                    privacy,
                    "derived_or_inferred",
                    relation=row["relation_type"],
                    score=row["score"],
                    record_key=row["connection_id"],
                ))

        if "capability_bridge_connections" in source.get("include", []) and "capability_bridge_connections" in available:
            for row in _sqlite_limited_rows(
                db,
                "select bridge_id, agent_id, agent_label, harness_id, harness_label, skill_id, skill_label, skill_family, node_skill_id, node_skill_label, node_skill_mode, node_id, node_label, card_id, card_label, turn_id, thread_id, platform, relation_type, strength_score, confidence from capability_bridge_connections",
                limit_per_table,
            ):
                agent = add_node(base_node("agent", row["agent_id"], row["agent_label"] or row["agent_id"], "agent", "derived_or_inferred"))
                skill = add_node(base_node("skill", row["skill_id"], row["skill_label"] or row["skill_id"], "skill", "derived_or_inferred", skill_family=row["skill_family"]))
                add_edge(_edge(agent, skill, "uses_skill", source_id, record_owner, privacy, "derived_or_inferred", relation=row["relation_type"], score=row["strength_score"], confidence=row["confidence"]))
                if row["node_id"]:
                    hapa_node = add_node(base_node("hapa_node", row["node_id"], row["node_label"] or row["node_id"], "hapa_node", "derived_or_inferred"))
                    add_edge(_edge(skill, hapa_node, "implements", source_id, record_owner, privacy, "derived_or_inferred", relation=row["relation_type"], score=row["strength_score"], confidence=row["confidence"]))
                if row["node_skill_id"]:
                    node_skill = add_node(base_node("hapa_node_skill", row["node_skill_id"], row["node_skill_label"] or row["node_skill_id"], "capability", "derived_or_inferred", mode=row["node_skill_mode"]))
                    add_edge(_edge(skill, node_skill, "relates_to", source_id, record_owner, privacy, "derived_or_inferred", relation=row["relation_type"], score=row["strength_score"], confidence=row["confidence"]))
                if row["card_id"]:
                    card = add_node(base_node("turn_card", row["card_id"], row["card_label"] or row["card_id"], "turn_card", "derived_or_inferred"))
                    add_edge(_edge(skill, card, "derived_from", source_id, record_owner, privacy, "derived_or_inferred", relation=row["relation_type"], score=row["strength_score"], confidence=row["confidence"]))
                if row["turn_id"]:
                    turn = add_node(base_node("ai_chat_turn", row["turn_id"], row["turn_id"], "artifact", "derived_or_inferred", platform=row["platform"], thread_id=row["thread_id"]))
                    add_edge(_edge(skill, turn, "derived_from", source_id, record_owner, privacy, "derived_or_inferred", relation=row["relation_type"], score=row["strength_score"], confidence=row["confidence"]))
                if row["harness_id"]:
                    harness = add_node(base_node("harness", row["harness_id"], row["harness_label"] or row["harness_id"], "capability", "derived_or_inferred"))
                    add_edge(_edge(agent, harness, "uses_skill", source_id, record_owner, privacy, "derived_or_inferred", relation="harness"))

    return {
        "schema": "hapa.graph.fragment.v1",
        "source_id": source_id,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "root": str(root),
            "limit_per_table": limit_per_table,
            "table_allowlist": source.get("include", []),
        },
    }


def _repo_graph_fragment(root: Path, source: dict[str, Any], *, limit: int) -> dict[str, Any]:
    source_id = str(source["id"])
    record_owner = str(source.get("record_owner") or source_id)
    privacy = str(source.get("privacy") or "private-local")
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(node: dict[str, Any]) -> str:
        if node["id"] not in seen:
            nodes.append(node)
            seen.add(node["id"])
        return node["id"]

    def base(record_type: str, key: str, label: str, node_type: str, **extra: Any) -> dict[str, Any]:
        return {
            "id": stable_id(source_id, record_type, key, label),
            "label": label,
            "type": node_type,
            "truth_status": "verified_source",
            "source_id": source_id,
            "record_owner": record_owner,
            "privacy": privacy,
            "record_type": record_type,
            "record_key": key,
            **extra,
        }

    repo = add(base(
        "repo",
        str(root),
        root.name,
        "repo",
        source_file=str(root),
        remote=source.get("metadata", {}).get("remote") if isinstance(source.get("metadata"), dict) else None,
        reviewed_commit=source.get("metadata", {}).get("reviewed_commit") if isinstance(source.get("metadata"), dict) else None,
    ))
    files = _iter_included_files(
        root,
        source,
        default_include=["README.md", "AGENTS.md", "docs/**/*.md", "hapa-node.json", "**/*.py", "**/*.ts", "**/*.js"],
        limit=limit if limit > 0 else None,
    )
    files = _limit_items(files, limit)
    for file_path in files:
        rel = file_path.relative_to(root).as_posix()
        file_node = add(base(
            "source_file",
            rel,
            rel,
            _file_node_type(file_path),
            source_file=str(file_path),
            extension=file_path.suffix,
            bytes=file_path.stat().st_size,
        ))
        edges.append(_edge(repo, file_node, "indexes", source_id, record_owner, privacy, "verified_source"))
        if file_path.name in {"README.md", "AGENTS.md", "hapa-node.json"}:
            capability = add(base(
                "capability",
                f"{rel}:protocol-surface",
                f"Protocol surface: {file_path.name}",
                "capability",
                source_file=str(file_path),
            ))
            edges.append(_edge(file_node, capability, "implements", source_id, record_owner, privacy, "verified_source"))

    return {
        "schema": "hapa.graph.fragment.v1",
        "source_id": source_id,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "root": str(root),
            "limit": limit,
            "file_count_sampled": len(files),
            "include": source.get("include"),
            "exclude": source.get("exclude"),
        },
    }


def _hapa_ecosystem_codebases_fragment(
    source: dict[str, Any],
    *,
    limit_per_codebase: int,
    full: bool,
    max_codebases: int | None,
) -> dict[str, Any]:
    source_id = str(source["id"])
    record_owner = str(source.get("record_owner") or source_id)
    privacy = str(source.get("privacy") or "private-local")
    discovery_config = source.get("discovery") if isinstance(source.get("discovery"), dict) else {}
    discovery = discover_hapa_codebases(
        node_map_path=discovery_config.get("node_map"),
        quest_audit_path=discovery_config.get("quest_keeper_audit"),
        overwatch_config_dir=discovery_config.get("overwatch_config_dir"),
        manifest_scan_roots=discovery_config.get("manifest_scan_roots"),
    )
    codebases = discovery["codebases"]
    if max_codebases is not None:
        codebases = codebases[:max_codebases]

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str, str]] = set()

    def add(node: dict[str, Any]) -> str:
        if node["id"] not in seen_nodes:
            nodes.append(node)
            seen_nodes.add(node["id"])
        return node["id"]

    def add_edge(edge: dict[str, Any]) -> None:
        key = (str(edge.get("source")), str(edge.get("target")), str(edge.get("type")), str(edge.get("relation", "")))
        if key not in seen_edges and edge.get("source") != edge.get("target"):
            edges.append(edge)
            seen_edges.add(key)

    def base(record_type: str, key: str, label: str, node_type: str, truth_status: str = "verified_source", **extra: Any) -> dict[str, Any]:
        return {
            "id": stable_id(source_id, record_type, key, label),
            "label": label,
            "type": node_type,
            "truth_status": truth_status,
            "source_id": source_id,
            "record_owner": record_owner,
            "privacy": privacy,
            "record_type": record_type,
            "record_key": key,
            **extra,
        }

    ast_status = _graphify_ast_status()
    codebase_summaries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    total_code_files = 0
    selected_code_files = 0

    for codebase in codebases:
        root = Path(codebase["path"])
        node_label = str(codebase.get("node_name") or codebase.get("node_id") or root.name)
        hapa_node = add(base(
            "hapa_node",
            str(codebase.get("node_id") or node_label),
            node_label,
            "hapa_node",
            status=codebase.get("status"),
            role=codebase.get("role"),
            project_id=codebase.get("project_id"),
            discovery_sources=codebase.get("sources", []),
        ))
        repo = add(base(
            "codebase",
            str(root),
            str(codebase.get("label") or root.name),
            "repo",
            source_file=str(root),
            node_id=codebase.get("node_id"),
            root_kind=codebase.get("root_kind"),
            marker_files=codebase.get("marker_files", []),
        ))
        add_edge(_edge(hapa_node, repo, "implements", source_id, record_owner, privacy, "verified_source"))

        detected = _detect_graphify_code_files(root)
        code_files = detected.get("code_files", [])
        total_code_files += len(code_files)
        if full or limit_per_codebase <= 0:
            selected = code_files
        else:
            selected = code_files[:limit_per_codebase]
        selected_code_files += len(selected)
        file_nodes = _add_code_file_nodes(
            selected,
            root=root,
            repo_id=repo,
            source_id=source_id,
            record_owner=record_owner,
            privacy=privacy,
            base=base,
            add=add,
            add_edge=add_edge,
        )

        summary = {
            "node_id": codebase.get("node_id"),
            "path": str(root),
            "exists": root.exists(),
            "code_files": len(code_files),
            "selected_files": len(selected),
            "full": full or limit_per_codebase <= 0,
            "skipped_sensitive_count": len(detected.get("skipped_sensitive", [])),
            "detect_engine": detected.get("engine"),
            "ast_ok": False,
        }
        if not root.exists() or not root.is_dir():
            summary["error"] = "missing_or_not_directory"
            errors.append({"codebase": str(root), "error": summary["error"]})
            codebase_summaries.append(summary)
            continue
        if not selected:
            summary["ast_ok"] = True
            summary["warning"] = "no_code_files_detected"
            codebase_summaries.append(summary)
            continue
        if not ast_status["available"]:
            summary["error"] = ast_status["error"]
            errors.append({"codebase": str(root), "error": ast_status["error"]})
            blocked = add(base(
                "ast_dependency",
                f"{root}:graphify-ast-unavailable",
                "Graphify AST unavailable",
                "concept",
                "blocked",
                codebase_root=str(root),
                dependency=ast_status.get("dependency"),
                error=ast_status.get("error"),
            ))
            add_edge(_edge(repo, blocked, "blocked_by", source_id, record_owner, privacy, "blocked"))
            codebase_summaries.append(summary)
            continue
        extraction = _run_graphify_ast(selected, root=root)
        summary["ast_ok"] = extraction.get("ok", False)
        summary["graphify_nodes"] = len(extraction.get("nodes", []))
        summary["graphify_edges"] = len(extraction.get("edges", []))
        if not extraction.get("ok"):
            summary["error"] = extraction.get("error", "graphify_ast_failed")
            errors.append({"codebase": str(root), "error": summary["error"]})
            codebase_summaries.append(summary)
            continue
        converted = _add_graphify_ast_nodes_edges(
            extraction,
            root=root,
            codebase=codebase,
            file_nodes=file_nodes,
            source_id=source_id,
            record_owner=record_owner,
            privacy=privacy,
            base=base,
            add=add,
            add_edge=add_edge,
        )
        summary.update(converted)
        codebase_summaries.append(summary)

    fragment = {
        "schema": "hapa.graph.fragment.v1",
        "source_id": source_id,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "full": full or limit_per_codebase <= 0,
            "limit_per_codebase": limit_per_codebase,
            "max_codebases": max_codebases,
            "node_root_count": discovery["node_root_count"],
            "codebase_count": len(codebases),
            "total_discovered_codebases": discovery["codebase_count"],
            "total_code_files": total_code_files,
            "selected_code_files": selected_code_files,
            "graphify_ast": ast_status,
        },
    }
    return {
        "ok": not errors and ast_status["available"],
        "fragment": fragment,
        "discovery": {
            "node_root_count": discovery["node_root_count"],
            "codebase_count": discovery["codebase_count"],
            "missing_count": discovery["missing_count"],
            "sources": discovery["sources"],
        },
        "ast": {
            "available": ast_status["available"],
            "dependency": ast_status.get("dependency"),
            "codebase_count": len(codebase_summaries),
            "total_code_files": total_code_files,
            "selected_code_files": selected_code_files,
            "codebases": codebase_summaries,
        },
        "errors": errors,
    }


def _add_code_file_nodes(
    files: list[str],
    *,
    root: Path,
    repo_id: str,
    source_id: str,
    record_owner: str,
    privacy: str,
    base,
    add,
    add_edge,
) -> dict[str, str]:
    file_nodes: dict[str, str] = {}
    for file_name in files:
        file_path = Path(file_name)
        rel = _relativize_to_root(file_path, root)
        node = add(base(
            "source_file",
            f"{root}:{rel}",
            rel,
            "source_file",
            source_file=rel,
            extension=file_path.suffix,
            bytes=_safe_file_size(file_path),
        ))
        file_nodes[rel] = node
        add_edge(_edge(repo_id, node, "indexes", source_id, record_owner, privacy, "verified_source"))
    return file_nodes


def _add_graphify_ast_nodes_edges(
    extraction: dict[str, Any],
    *,
    root: Path,
    codebase: dict[str, Any],
    file_nodes: dict[str, str],
    source_id: str,
    record_owner: str,
    privacy: str,
    base,
    add,
    add_edge,
) -> dict[str, int]:
    id_map: dict[str, str] = {}
    ast_node_count = 0
    ast_edge_count = 0
    for node in extraction.get("nodes", []):
        original_id = str(node.get("id") or node.get("label") or "")
        label = str(node.get("label") or original_id or "unnamed")
        rel_file = _relativize_to_root(Path(str(node.get("source_file") or "")), root) if node.get("source_file") else ""
        if rel_file and _looks_like_graphify_file_node(node, rel_file):
            id_map[original_id] = file_nodes.get(rel_file) or add(base(
                "source_file",
                f"{root}:{rel_file}",
                rel_file,
                "source_file",
                source_file=rel_file,
                extension=Path(rel_file).suffix,
            ))
            continue
        key = f"{codebase.get('path')}:{rel_file}:{original_id}:{node.get('source_location') or ''}"
        ast_node = add(base(
            "ast_symbol",
            key,
            label,
            _graphify_ast_node_type(node),
            map_graphify_confidence(node.get("confidence") or "EXTRACTED"),
            graphify_id=original_id,
            codebase_path=str(codebase.get("path")),
            node_id=codebase.get("node_id"),
            source_file=rel_file or None,
            source_location=node.get("source_location"),
            file_type=node.get("file_type"),
        ))
        id_map[original_id] = ast_node
        ast_node_count += 1
        if rel_file and rel_file in file_nodes:
            add_edge(_edge(file_nodes[rel_file], ast_node, "defines", source_id, record_owner, privacy, "verified_source"))
            ast_edge_count += 1

    for edge in extraction.get("edges", extraction.get("links", [])):
        src = str(edge.get("source", edge.get("from", "")))
        tgt = str(edge.get("target", edge.get("to", "")))
        if src not in id_map or tgt not in id_map:
            continue
        relation = str(edge.get("relation") or edge.get("type") or "relates_to")
        mapped = _map_graphify_relation(relation)
        add_edge(_edge(
            id_map[src],
            id_map[tgt],
            mapped,
            source_id,
            record_owner,
            privacy,
            map_graphify_confidence(edge.get("confidence") or "EXTRACTED"),
            relation=relation,
            source_file=_relativize_to_root(Path(str(edge.get("source_file") or "")), root) if edge.get("source_file") else None,
            source_location=edge.get("source_location"),
            confidence=edge.get("confidence"),
            weight=edge.get("weight"),
        ))
        ast_edge_count += 1
    return {"hapa_ast_nodes": ast_node_count, "hapa_ast_edges": ast_edge_count}


def _markdown_graph_fragment(root: Path, source: dict[str, Any], *, limit: int) -> dict[str, Any]:
    source_id = str(source["id"])
    record_owner = str(source.get("record_owner") or source_id)
    privacy = str(source.get("privacy") or "private-local")
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_edges: set[tuple[str, str, str, str, str]] = set()
    directory_nodes: dict[str, str] = {}
    heading_node_count = 0
    wikilink_edge_count = 0

    def add(node: dict[str, Any]) -> str:
        if node["id"] not in seen:
            nodes.append(node)
            seen.add(node["id"])
        return node["id"]

    def add_edge(edge: dict[str, Any]) -> None:
        key = (
            str(edge.get("source")),
            str(edge.get("target")),
            str(edge.get("type")),
            str(edge.get("source_id")),
            str(edge.get("relation", "")),
        )
        if key not in seen_edges and edge.get("source") != edge.get("target"):
            edges.append(edge)
            seen_edges.add(key)

    def node_base(record_type: str, key: str, label: str, node_type: str, **extra: Any) -> dict[str, Any]:
        return {
            "id": stable_id(source_id, record_type, key, label),
            "label": label,
            "type": node_type,
            "truth_status": "verified_source",
            "source_id": source_id,
            "record_owner": record_owner,
            "privacy": privacy,
            "record_type": record_type,
            "record_key": key,
            **extra,
        }

    collection = add(node_base(
        "markdown_collection",
        str(root),
        source.get("label") or root.name,
        "concept",
        source_file=str(root),
        article_type="markdown_collection",
    ))

    def directory_node(rel_dir: str) -> str:
        normalized = rel_dir.strip("/")
        if not normalized:
            return collection
        if normalized in directory_nodes:
            return directory_nodes[normalized]
        parent = Path(normalized).parent.as_posix()
        if parent == ".":
            parent = ""
        node_id = add(node_base(
            "markdown_directory",
            normalized,
            normalized,
            "concept",
            source_file=str(root / normalized),
            article_type="directory",
        ))
        directory_nodes[normalized] = node_id
        add_edge(_edge(directory_node(parent), node_id, "indexes", source_id, record_owner, privacy, "verified_source"))
        return node_id

    node_map = root / "NODE_MAP.md"
    if node_map.exists():
        for index, row in enumerate(_limit_items(_parse_node_map_rows(node_map), limit)):
            label = row.get("Node") or row.get("node") or f"Node row {index + 1}"
            local_path = row.get("Local path") or row.get("local path") or ""
            manifest_status = _manifest_status_for_local_path(local_path, root)
            node_id = add(node_base(
                "hapa_node_map_row",
                label,
                label,
                "hapa_node",
                source_file=str(node_map),
                local_path=local_path,
                status=row.get("Status"),
                role=row.get("Role"),
                ecosystem_meaning=row.get("Ecosystem meaning"),
                manifest_status=manifest_status,
            ))
            if manifest_status == "missing":
                gap = add(node_base(
                    "manifest_gap",
                    f"{label}:manifest",
                    f"Missing manifest: {label}",
                    "concept",
                    truth_status="blocked",
                ))
                add_edge(_edge(node_id, gap, "blocked_by", source_id, record_owner, privacy, "blocked"))

    for manifest in _limit_items(list(root.rglob("hapa-node.json")), limit):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        label = str(data.get("display_name") or data.get("id") or manifest.parent.name)
        manifest_node = add(node_base(
            "hapa_node_manifest",
            str(data.get("id") or manifest.as_posix()),
            label,
            "hapa_node",
            source_file=str(manifest),
            status=data.get("status"),
            role=data.get("role"),
        ))
        board = data.get("board", {}).get("project_id") if isinstance(data.get("board"), dict) else None
        if board:
            board_node = add(node_base("kanban_project", board, board, "kanban_card", source_file=str(manifest)))
            add_edge(_edge(manifest_node, board_node, "tracks", source_id, record_owner, privacy, "verified_source"))

    markdown_files = _iter_included_files(
        root,
        source,
        default_include=["*.md", "**/*.md"],
        limit=limit if limit > 0 else None,
    )
    selected_markdown_files = _limit_items(markdown_files, limit)
    max_headings = int(source.get("max_headings_per_page") or 4)
    for md in selected_markdown_files:
        if md.name == "NODE_MAP.md":
            continue
        rel = md.relative_to(root).as_posix()
        body = md.read_text(encoding="utf-8", errors="replace")
        frontmatter, content = _parse_frontmatter(body)
        title = str(frontmatter.get("title") or _title_from_markdown(content) or md.stem.replace("-", " ").title())
        article_type = str(frontmatter.get("type") or _markdown_article_type(md, rel, content))
        article_node_type = "protocol_card" if _is_protocol_markdown(md, rel, frontmatter, content) else "wiki_article"
        article = add(node_base(
            "markdown_page",
            rel,
            title,
            article_node_type,
            source_file=str(md),
            article_type=article_type,
            category=_markdown_category(rel, frontmatter),
            status=frontmatter.get("status"),
            tags=frontmatter.get("tags"),
            bytes=md.stat().st_size,
        ))
        add_edge(_edge(directory_node(Path(rel).parent.as_posix() if "/" in rel else ""), article, "indexes", source_id, record_owner, privacy, "verified_source"))
        for heading in _markdown_headings(content, max_headings=max_headings):
            heading_node = add(node_base(
                "markdown_heading",
                f"{rel}#{heading['slug']}",
                heading["text"],
                "protocol_card" if article_node_type == "protocol_card" else "concept",
                source_file=str(md),
                heading_level=heading["level"],
                article=rel,
            ))
            heading_node_count += 1
            add_edge(_edge(article, heading_node, "indexes", source_id, record_owner, privacy, "verified_source", relation="heading"))
        for target in _wikilinks(content)[:20]:
            concept = add(node_base(
                "wikilink_target",
                target,
                target,
                "concept",
                truth_status="derived_or_inferred",
                source_file=str(md),
            ))
            add_edge(_edge(article, concept, "mentions", source_id, record_owner, privacy, "derived_or_inferred"))
            wikilink_edge_count += 1

    return {
        "schema": "hapa.graph.fragment.v1",
        "source_id": source_id,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "root": str(root),
            "limit": limit,
            "node_map_exists": node_map.exists(),
            "full": limit <= 0,
            "markdown_pages_available": len(markdown_files),
            "markdown_pages_count_mode": "full" if limit <= 0 else "bounded_sample",
            "markdown_pages_selected": len(selected_markdown_files),
            "directory_nodes": len(directory_nodes),
            "heading_nodes": heading_node_count,
            "wikilink_edges": wikilink_edge_count,
        },
    }


def _kanban_graph_fragment(root: Path, source: dict[str, Any], *, limit: int) -> dict[str, Any]:
    source_id = str(source["id"])
    record_owner = str(source.get("record_owner") or source_id)
    privacy = str(source.get("privacy") or "private-local")
    project_id = str(source.get("project_id"))
    config_path = root / "config" / "projects" / f"{project_id}.json"
    data_path = root / "data" / project_id / "events.ndjson"
    seed_path = root / "seed" / f"{project_id}.events.ndjson"
    event_path = data_path if data_path.exists() else seed_path

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add(node: dict[str, Any]) -> str:
        if node["id"] not in seen:
            nodes.append(node)
            seen.add(node["id"])
        return node["id"]

    def base(record_type: str, key: str, label: str, node_type: str, truth: str = "verified_source", **extra: Any) -> dict[str, Any]:
        return {
            "id": stable_id(source_id, record_type, key, label),
            "label": label,
            "type": node_type,
            "truth_status": truth,
            "source_id": source_id,
            "record_owner": record_owner,
            "privacy": privacy,
            "record_type": record_type,
            "record_key": key,
            **extra,
        }

    project_label = project_id
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            project_label = config.get("name") or project_id
        except json.JSONDecodeError:
            pass
    project_node = add(base("kanban_project", project_id, project_label, "kanban_card", source_file=str(config_path)))

    if not event_path.exists():
        gap = add(base("kanban_event_log_gap", project_id, f"Missing event log: {project_id}", "concept", "blocked"))
        edges.append(_edge(project_node, gap, "blocked_by", source_id, record_owner, privacy, "blocked"))
        events: list[dict[str, Any]] = []
    else:
        events = _limit_items(_read_ndjson(event_path), limit)

    for event in events:
        actor = str(event.get("actor") or "unknown")
        actor_node = add(base("kanban_actor", actor, actor, "agent", source_file=str(event_path)))
        event_type = str(event.get("type") or "event")
        task_id = event.get("task_id") or event.get("payload", {}).get("taskId")
        if event_type == "task_created" or task_id:
            payload = event.get("payload", {})
            label = payload.get("title") or str(task_id)
            task_node = add(base(
                "kanban_task",
                str(task_id),
                label,
                "kanban_card",
                source_file=str(event_path),
                column=payload.get("column"),
                owner=payload.get("owner"),
                priority=payload.get("priority"),
                lane=payload.get("lane"),
                event_type=event_type,
            ))
            edges.append(_edge(project_node, task_node, "tracks", source_id, record_owner, privacy, "verified_source"))
            edges.append(_edge(actor_node, task_node, "mentions", source_id, record_owner, privacy, "verified_source", relation=event_type))
            node_label = payload.get("node")
            if node_label:
                hapa_node = add(base("hapa_node_ref", str(node_label), str(node_label), "hapa_node", source_file=str(event_path)))
                edges.append(_edge(task_node, hapa_node, "tracks", source_id, record_owner, privacy, "verified_source"))
        else:
            event_node = add(base("kanban_event", str(event.get("id")), event_type, "artifact", source_file=str(event_path), event_type=event_type))
            edges.append(_edge(project_node, event_node, "tracks", source_id, record_owner, privacy, "verified_source"))
            edges.append(_edge(actor_node, event_node, "mentions", source_id, record_owner, privacy, "verified_source", relation=event_type))

        if event_type == "review_decision":
            decision = event.get("payload", {}).get("decision", "review")
            decision_node = add(base(
                "review_decision",
                str(event.get("id")),
                f"Review decision: {decision}",
                "artifact",
                source_file=str(event_path),
                decision=decision,
            ))
            if task_id:
                task_node = add(base("kanban_task", str(task_id), str(task_id), "kanban_card", source_file=str(event_path)))
                edges.append(_edge(task_node, decision_node, "derived_from", source_id, record_owner, privacy, "verified_source"))

        for link in event.get("links", [])[:5]:
            href = str(link.get("href") or "")
            label = str(link.get("label") or href or "Evidence")
            if not href:
                continue
            evidence = add(base("evidence_link", href, label, "artifact", source_file=str(event_path), href=href))
            if task_id:
                task_node = add(base("kanban_task", str(task_id), str(task_id), "kanban_card", source_file=str(event_path)))
                edges.append(_edge(task_node, evidence, "mentions", source_id, record_owner, privacy, "verified_source"))
            else:
                edges.append(_edge(project_node, evidence, "mentions", source_id, record_owner, privacy, "verified_source"))

    return {
        "schema": "hapa.graph.fragment.v1",
        "source_id": source_id,
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "root": str(root),
            "project_id": project_id,
            "event_log": str(event_path),
            "event_count_sampled": len(events),
            "append_only": true_like(True),
        },
    }


def _edge(
    source: str,
    target: str,
    edge_type: str,
    source_id: str,
    record_owner: str,
    privacy: str,
    truth_status: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "type": edge_type,
        "truth_status": truth_status,
        "source_id": source_id,
        "record_owner": record_owner,
        "privacy": privacy,
        **extra,
    }


def _default_hapa_ecosystem_source() -> dict[str, Any]:
    return {
        "id": "hapa-ecosystem-codebases",
        "kind": "hapa_ecosystem_codebases",
        "root": str(DEFAULT_NODE_MAP.parent),
        "privacy": "private-local",
        "authority": "read-only",
        "record_owner": "hapa-graphify",
        "refresh_mode": "changed-source",
        "discovery": {
            "node_map": str(DEFAULT_NODE_MAP),
            "quest_keeper_audit": str(DEFAULT_QUEST_KEEPER_AUDIT),
            "overwatch_config_dir": str(DEFAULT_OVERWATCH_CONFIG_DIR),
        },
    }


def _resolve_hapa_path(value: str | Path, *, base: Path) -> Path | None:
    text = str(value).strip().strip("`")
    if not text or text in {"-", "unknown"}:
        return None
    for name, default in sorted(HAPA_PATH_DEFAULTS.items(), key=lambda item: len(item[0]), reverse=True):
        replacement = os.environ.get(name, default)
        text = text.replace(f"${name}", replacement).replace(f"${{{name}}}", replacement)
    text = os.path.expandvars(text)
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = (base / path).resolve()
    return path


def _normalize_node_id(value: str) -> str:
    return _normalize_token(value).replace("-", "-")


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    output: list[Path] = []
    for path in paths:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        key = str(resolved)
        if key not in seen:
            output.append(resolved)
            seen.add(key)
    return output


def _iter_hapa_manifests(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir():
        return []
    manifests: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        path = Path(dirpath)
        dirnames[:] = [name for name in dirnames if not _is_skipped_codebase_dir(path / name, root)]
        if "hapa-node.json" in filenames:
            manifests.append(path / "hapa-node.json")
    return sorted(manifests)


def _discover_codebase_roots(node_roots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    codebases: dict[str, dict[str, Any]] = {}

    def add_codebase(root: Path, node: dict[str, Any], *, root_kind: str, marker_files: list[str] | None = None) -> None:
        if not root.exists() or not root.is_dir():
            return
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root
        key = str(resolved)
        item = codebases.setdefault(key, {
            "id": stable_id("hapa-ecosystem-codebases", "codebase", key, resolved.name),
            "path": key,
            "label": resolved.name,
            "node_id": node.get("node_id"),
            "node_name": node.get("name") or node.get("node_id"),
            "status": node.get("status"),
            "role": node.get("role"),
            "project_id": node.get("project_id"),
            "root_kind": root_kind,
            "marker_files": [],
            "sources": [],
        })
        for marker in marker_files or []:
            if marker not in item["marker_files"]:
                item["marker_files"].append(marker)
        for source in node.get("sources", []):
            if source not in item["sources"]:
                item["sources"].append(source)
        if root_kind == "node-root":
            item["root_kind"] = "node-root"

    for node in node_roots:
        root = Path(str(node.get("path") or ""))
        if not node.get("exists") or not node.get("is_dir"):
            continue
        if _directory_has_codebase_signal(root):
            add_codebase(root, node, root_kind="node-root", marker_files=_marker_files_for_root(root))
        for marker in _iter_codebase_markers(root):
            add_codebase(marker.parent, node, root_kind="nested-codebase", marker_files=[marker.name])

    return sorted(codebases.values(), key=lambda item: (str(item.get("node_id")), str(item.get("path"))))


def _directory_has_codebase_signal(root: Path) -> bool:
    if _marker_files_for_root(root):
        return True
    try:
        return any(
            path.is_file() and path.suffix.lower() in CODE_EXTENSIONS and not _is_blocked_source_path(path.name)
            for path in root.iterdir()
        )
    except OSError:
        return False


def _marker_files_for_root(root: Path) -> list[str]:
    return sorted(marker for marker in CODEBASE_MARKERS if (root / marker).exists())


def _iter_codebase_markers(root: Path) -> list[Path]:
    markers: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        path = Path(dirpath)
        dirnames[:] = [name for name in dirnames if not _is_skipped_codebase_dir(path / name, root)]
        for filename in sorted(set(filenames) & CODEBASE_MARKERS):
            marker = path / filename
            rel = _relativize_to_root(marker, root)
            if not _is_blocked_source_path(rel):
                markers.append(marker)
    return sorted(markers)


def _is_skipped_codebase_dir(path: Path, root: Path) -> bool:
    name = path.name
    if (
        name in CODEBASE_SKIP_DIRS
        or name.startswith(".venv")
        or name.startswith("venv")
        or name.startswith(".conda")
        or name.startswith("conda")
    ):
        return True
    rel = _relativize_to_root(path, root)
    return _is_blocked_source_path(rel) or rel in CODEBASE_SKIP_DIRS or any(
        rel == item or rel.startswith(f"{item}/") for item in CODEBASE_SKIP_DIRS if "/" in item
    )


def _detect_graphify_code_files(root: Path) -> dict[str, Any]:
    _ensure_graphify_import_path()
    try:
        from graphify.detect import detect
        detected = detect(root, google_workspace=False, extra_excludes=list(CODEBASE_SKIP_DIRS))
        files = [
            str(Path(item))
            for item in detected.get("files", {}).get("code", [])
            if not _is_blocked_source_path(_relativize_to_root(Path(item), root))
        ]
        return {
            "ok": True,
            "engine": "graphify.detect",
            "code_files": sorted(files),
            "skipped_sensitive": detected.get("skipped_sensitive", []),
            "total_files": detected.get("total_files"),
            "warning": detected.get("warning"),
        }
    except Exception as exc:
        files = [
            str(path)
            for path in _iter_local_code_files(root)
            if not _is_blocked_source_path(_relativize_to_root(path, root))
        ]
        return {
            "ok": True,
            "engine": "fallback-rglob",
            "code_files": sorted(files),
            "skipped_sensitive": [],
            "warning": f"graphify.detect unavailable: {type(exc).__name__}: {exc}",
        }


def _iter_local_code_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        path = Path(dirpath)
        dirnames[:] = [name for name in dirnames if not _is_skipped_codebase_dir(path / name, root)]
        for filename in filenames:
            candidate = path / filename
            if candidate.suffix.lower() in CODE_EXTENSIONS:
                files.append(candidate)
    return sorted(files)


def _graphify_ast_status() -> dict[str, Any]:
    _ensure_graphify_import_path()
    try:
        import tree_sitter  # noqa: F401
        from graphify.extract import extract  # noqa: F401
        return {"available": True, "dependency": "graphify.extract/tree_sitter", "error": None}
    except Exception as exc:
        return {
            "available": False,
            "dependency": "graphify.extract/tree_sitter",
            "error": f"{type(exc).__name__}: {exc}",
        }


def _run_graphify_ast(files: list[str], *, root: Path) -> dict[str, Any]:
    _ensure_graphify_import_path()
    try:
        from graphify.extract import extract
        result = extract([Path(item) for item in files], cache_root=root, parallel=True, max_workers=4)
        return {
            "ok": True,
            "nodes": result.get("nodes", []),
            "edges": result.get("edges", result.get("links", [])),
            "raw": {key: value for key, value in result.items() if key not in {"nodes", "edges", "links"}},
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "nodes": [], "edges": []}


def _ensure_graphify_import_path() -> None:
    if (DEFAULT_GRAPHIFY_UPSTREAM / "graphify").is_dir():
        path = str(DEFAULT_GRAPHIFY_UPSTREAM)
        if path not in sys.path:
            sys.path.insert(0, path)


def _relativize_to_root(path: Path, root: Path) -> str:
    text = str(path)
    if not text:
        return ""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except (OSError, ValueError):
        try:
            return path.relative_to(root).as_posix()
        except ValueError:
            return text.replace("\\", "/")


def _safe_file_size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def _looks_like_graphify_file_node(node: dict[str, Any], rel_file: str) -> bool:
    label = str(node.get("label") or "")
    return bool(rel_file) and (label == Path(rel_file).name or label == rel_file or Path(label).suffix.lower() in CODE_EXTENSIONS)


def _graphify_ast_node_type(node: dict[str, Any]) -> str:
    if _looks_like_graphify_file_node(node, str(node.get("source_file") or "")):
        return "source_file"
    return "capability"


def _map_graphify_relation(relation: str) -> str:
    relation = relation.strip()
    if relation in EDGE_TYPES:
        return relation
    if relation in {"contains", "method", "field", "parameter_type", "return_type"}:
        return "defines"
    if relation in {"imports_from", "re_exports"}:
        return "imports"
    if relation in {"inherits", "mixes_in", "embeds"}:
        return "implements"
    if relation in {"references", "reference", "uses"}:
        return "relates_to"
    return "relates_to"


def _sqlite_table_names(db: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in db.execute("select name from sqlite_master where type in ('table','view')")
    }


def _sqlite_limited_rows(db: sqlite3.Connection, sql: str, limit: int):
    if limit <= 0:
        return db.execute(sql)
    return db.execute(f"{sql} limit ?", (limit,))


def _subject_type_to_node_type(subject_type: str) -> str:
    text = str(subject_type).lower()
    if "node" in text:
        return "hapa_node"
    if "skill" in text:
        return "skill"
    if "card" in text:
        return "turn_card"
    if "article" in text or "wiki" in text:
        return "wiki_article"
    return "concept"


def _file_node_type(path: Path) -> str:
    if path.suffix.lower() in {".md", ".mdx", ".txt", ".rst"}:
        return "wiki_article"
    if path.suffix.lower() in {".json", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".mp4", ".mov", ".mp3", ".wav"}:
        return "artifact"
    return "source_file"


def _parse_node_map_rows(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    headers: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or not stripped.endswith("|"):
            continue
        cells = [_clean_md_cell(cell) for cell in stripped.strip("|").split("|")]
        if cells and all(set(cell) <= {"-", ":"} for cell in cells):
            continue
        if not headers:
            headers = cells
            continue
        if headers and len(cells) == len(headers):
            rows.append(dict(zip(headers, cells)))
    return rows


def _clean_md_cell(value: str) -> str:
    text = value.strip()
    if text.startswith("`") and text.endswith("`"):
        text = text[1:-1]
    return text


def _manifest_status_for_local_path(local_path: str, base_root: Path) -> str:
    if not local_path:
        return "unknown"
    if "$" in local_path:
        return "unresolved_variable_path"
    path = Path(local_path)
    if not path.is_absolute():
        path = (base_root / path).resolve()
    if (path / "hapa-node.json").exists():
        return "present"
    if path.exists():
        return "missing"
    return "unknown"


def _iter_included_files(root: Path, source: dict[str, Any], *, default_include: list[str], limit: int | None = None) -> list[Path]:
    include = source.get("include") or default_include
    exclude = source.get("exclude") or []
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if _is_blocked_source_path(rel):
            continue
        if not _matches_any(rel, include):
            continue
        if _matches_any(rel, exclude):
            continue
        files.append(path)
        if limit is not None and limit > 0 and len(files) >= limit:
            break
    return sorted(files)


def _limit_items(items: list[Any], limit: int) -> list[Any]:
    if limit <= 0:
        return items
    return items[:limit]


def _matches_any(rel: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatch(rel, pattern):
            return True
        if pattern.startswith("**/") and fnmatch.fnmatch(rel, pattern[3:]):
            return True
        if "/**/" in pattern and fnmatch.fnmatch(rel, pattern.replace("/**/", "/")):
            return True
    return False


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    raw = text[4:end].strip()
    data: dict[str, Any] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("- ") and current_key:
            data.setdefault(current_key, [])
            if isinstance(data[current_key], list):
                data[current_key].append(stripped[2:].strip())
            continue
        if ":" in stripped:
            key, value = stripped.split(":", 1)
            current_key = key.strip()
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                data[current_key] = [item.strip().strip("\"'") for item in value[1:-1].split(",") if item.strip()]
            elif value:
                data[current_key] = value.strip("\"'")
            else:
                data[current_key] = []
    return data, text[end + 4:].lstrip("\n")


def _title_from_markdown(text: str) -> str | None:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _markdown_headings(text: str, *, max_headings: int) -> list[dict[str, Any]]:
    if max_headings <= 0:
        return []
    headings: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if not match:
            continue
        label = re.sub(r"\s+#*$", "", match.group(2)).strip()
        if not label:
            continue
        headings.append({
            "level": len(match.group(1)),
            "text": label,
            "slug": _normalize_token(label),
        })
        if len(headings) >= max_headings:
            break
    return headings


def _markdown_article_type(path: Path, rel: str, content: str) -> str:
    lowered = f"{rel}/{path.name}".lower()
    if "protocol" in lowered:
        return "protocol"
    if "operation" in lowered or "ops" in lowered:
        return "operations"
    if "capabilit" in lowered or "skill" in lowered:
        return "capability"
    if "card" in lowered:
        return "card"
    if "node" in lowered:
        return "node"
    if _title_from_markdown(content):
        return "markdown"
    return "document"


def _markdown_category(rel: str, frontmatter: dict[str, Any]) -> str:
    category = frontmatter.get("category")
    if category:
        return str(category)
    first = rel.split("/", 1)[0]
    return first if first and first != rel else "root"


def _is_protocol_markdown(path: Path, rel: str, frontmatter: dict[str, Any], content: str) -> bool:
    text = " ".join([
        rel,
        path.name,
        str(frontmatter.get("type") or ""),
        str(frontmatter.get("tags") or ""),
        _title_from_markdown(content) or "",
    ]).lower()
    return "protocol" in text or "standard" in text or "runbook" in text


def _wikilinks(text: str) -> list[str]:
    links = []
    for match in re.finditer(r"\[\[([^\]]+)\]\]", text):
        target = match.group(1).split("|", 1)[0].strip()
        if target and target not in links:
            links.append(target)
    return links


def _read_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({
                "id": stable_id("ndjson", "parse_error", line, "Parse error"),
                "type": "protocol_note",
                "actor": "hapa-graphify",
                "payload": {"body": "Unparseable NDJSON event"},
            })
    return rows


def true_like(value: bool) -> bool:
    return bool(value)


def _summarize_kanban(root: Path, source: dict[str, Any]) -> dict[str, Any]:
    project_id = source.get("project_id")
    paths = {
        "config": root / "config" / "projects" / f"{project_id}.json",
        "seed": root / "seed" / f"{project_id}.events.ndjson",
        "data": root / "data" / project_id / "events.ndjson",
    }
    counts = {}
    for key, path in paths.items():
        counts[f"{key}_exists"] = path.exists()
        if path.suffix == ".ndjson" and path.exists():
            counts[f"{key}_events"] = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    return {"kanban": counts, "source_signature": _multi_file_signature([p for p in paths.values() if p.exists()])}


def _summarize_files(root: Path, source: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    include = source.get("include") or ["**/*"]
    exclude = list(registry.get("default_exclude", [])) + list(source.get("exclude", []))
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if _is_blocked_source_path(rel):
            continue
        if not any(fnmatch.fnmatch(rel, pattern) for pattern in include):
            continue
        if any(fnmatch.fnmatch(rel, pattern) for pattern in exclude):
            continue
        files.append(path)
    return {
        "file_count": len(files),
        "source_signature": _multi_file_signature(files[:1000]),
        "sample": [p.relative_to(root).as_posix() for p in files[:10]],
    }


def _safe_sql_identifier(value: str) -> bool:
    return bool(value) and all(ch.isalnum() or ch == "_" for ch in value)


def _is_blocked_source_path(rel: str) -> bool:
    return is_credential_path(rel)


def _redact_private_string(value: str) -> str:
    if "/Users/" not in value:
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    suffix = Path(value).suffix
    return f"redacted://local/{digest}{suffix}"


def _normalize_token(value: str) -> str:
    text = str(value).strip().casefold()
    cleaned = []
    last_dash = False
    for ch in text:
        if ch.isalnum():
            cleaned.append(ch)
            last_dash = False
        elif not last_dash:
            cleaned.append("-")
            last_dash = True
    return "".join(cleaned).strip("-") or "unknown"


def _graphify_file_type_to_hapa(file_type: str | None) -> str:
    if file_type == "code":
        return "capability"
    if file_type in {"document", "paper", "rationale"}:
        return "wiki_article"
    if file_type == "image":
        return "artifact"
    return "concept"


def _file_signature(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.name.encode("utf-8"))
    h.update(str(path.stat().st_size).encode("ascii"))
    h.update(str(int(path.stat().st_mtime)).encode("ascii"))
    return h.hexdigest()


def _multi_file_signature(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for path in sorted(paths):
        h.update(path.as_posix().encode("utf-8"))
        try:
            h.update(str(path.stat().st_size).encode("ascii"))
            h.update(str(int(path.stat().st_mtime)).encode("ascii"))
        except OSError:
            h.update(b"missing")
    return h.hexdigest()
