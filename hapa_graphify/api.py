from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from .core import (
    ROOT,
    append_since_last_success,
    board_checkpoint,
    browse_graph_nodes,
    build_source_fragment,
    capabilities,
    discover_hapa_codebases,
    explain_graph_node,
    export_graph,
    graph_group_neighbors,
    health,
    graph_overview,
    ingest_dry_run,
    list_ledger_entries,
    list_sources,
    path_between,
    query_graph,
    reconcile_against,
    report_summaries,
    review_suggestions_for_source,
    run_hapa_ecosystem_ast_analysis,
    run_hapa_knowledge_analysis,
    smoke,
    telemetry_probe,
)
from .writeback import plan_writeback


class HapaGraphifyHandler(BaseHTTPRequestHandler):
    server_version = "hapa-graphify/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/ui", "/ui/"}:
            self._send_ui()
            return
        query = parse_qs(parsed.query)
        result = route_request("GET", parsed.path, query)
        self._send_json(result)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)
        body = self._read_json_body()
        result = route_request("POST", parsed.path, query, body)
        self._send_json(result)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {"_invalid_json": True}
        return data if isinstance(data, dict) else {"value": data}

    def _send_json(self, result: dict[str, Any]) -> None:
        status = HTTPStatus.OK if result.get("ok") else HTTPStatus.BAD_REQUEST
        payload = json.dumps(result, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_ui(self) -> None:
        path = ROOT / "ui" / "index.html"
        if not path.exists():
            self._send_json({"ok": False, "error": "ui_not_found"})
            return
        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


def route_request(
    method: str,
    path: str,
    query: dict[str, list[str]],
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = body or {}
    if body.get("_invalid_json"):
        return {"ok": False, "error": "invalid_json"}

    if method == "GET" and path == "/health":
        return health(deep=_bool_arg(query, "deep", False))
    if method == "GET" and path == "/capabilities":
        return capabilities()
    if method == "GET" and path == "/api/smoke":
        return smoke(dry_run=_bool_arg(query, "dry_run", True))
    if method == "GET" and path == "/api/sources":
        return list_sources()
    if method == "GET" and path == "/api/runs":
        return list_ledger_entries(limit=_int_arg(query, "limit", 20))
    if method == "GET" and path == "/api/reports":
        return report_summaries()
    if method == "GET" and path == "/api/map":
        return graph_overview(
            kind=_str_arg(query, "kind", "all"),
            level=_str_arg(query, "level", "community"),
            limit=_int_arg(query, "limit", 80),
            edge_limit=_int_arg(query, "edge_limit", 220),
        )
    if method == "GET" and path == "/api/map/neighbors":
        group_id = _str_arg(query, "id", "")
        if not group_id:
            return {"ok": False, "error": "id is required"}
        return graph_group_neighbors(
            group_id,
            kind=_str_arg(query, "kind", "all"),
            level=_str_arg(query, "level", "source_type"),
            limit=_int_arg(query, "limit", 24),
            edge_limit=_int_arg(query, "edge_limit", 80),
        )
    if method == "GET" and path == "/api/fragment":
        source = _str_arg(query, "source", "")
        if not source:
            return {"ok": False, "error": "source is required"}
        return build_source_fragment(
            source,
            limit_per_table=0 if _bool_arg(query, "full", False) else _int_arg(query, "limit", 100),
            full=_bool_arg(query, "full", False),
            max_codebases=_optional_int_arg(query, "max_codebases"),
        )
    if method == "GET" and path == "/api/query":
        q = _str_arg(query, "q", "")
        if not q:
            return {"ok": False, "error": "q is required"}
        return query_graph(
            q,
            source_id=_str_arg(query, "graph_source", "all"),
            limit=_int_arg(query, "limit", 20),
            limit_per_source=_int_arg(query, "limit_per_source", 50),
            node_type=_str_arg(query, "node_type", "") or None,
            truth_status=_str_arg(query, "truth_status", "") or None,
        )
    if method == "GET" and path == "/api/browse":
        return browse_graph_nodes(
            source_id=_str_arg(query, "source", "all"),
            query=_str_arg(query, "q", ""),
            limit=_int_arg(query, "limit", 50),
            offset=_int_arg(query, "offset", 0),
            limit_per_source=_optional_int_arg(query, "limit_per_source"),
            node_type=_str_arg(query, "node_type", "") or None,
            truth_status=_str_arg(query, "truth_status", "") or None,
        )
    if method == "GET" and path == "/api/path":
        start = _str_arg(query, "source", "")
        target = _str_arg(query, "target", "")
        if not start or not target:
            return {"ok": False, "error": "source and target are required"}
        return path_between(
            start,
            target,
            source_id=_str_arg(query, "graph_source", "all"),
            max_depth=_int_arg(query, "max_depth", 6),
            limit_per_source=_int_arg(query, "limit_per_source", 50),
        )
    if method == "GET" and path == "/api/explain":
        identifier = _str_arg(query, "id", "")
        if not identifier:
            return {"ok": False, "error": "id is required"}
        return explain_graph_node(
            identifier,
            source_id=_str_arg(query, "graph_source", "all"),
            limit_per_source=_int_arg(query, "limit_per_source", 50),
        )
    if method == "GET" and path == "/api/review-suggestions":
        source = _str_arg(query, "source", "")
        if not source:
            return {"ok": False, "error": "source is required"}
        return review_suggestions_for_source(source, limit_per_table=_int_arg(query, "limit", 100))
    if method == "GET" and path == "/api/telemetry/probe":
        urls = query.get("url") or None
        return telemetry_probe(urls)
    if method == "GET" and path == "/api/append":
        return append_since_last_success(dry_run=_bool_arg(query, "dry_run", True))
    if method == "GET" and path == "/api/reconcile":
        return reconcile_against(
            _str_arg(query, "against", "second-brain"),
            dry_run=_bool_arg(query, "dry_run", True),
        )
    if method == "GET" and path == "/api/export":
        return export_graph(
            source_id=_str_arg(query, "source", "all"),
            dry_run=_bool_arg(query, "dry_run", True),
            public=_bool_arg(query, "public", False),
            limit_per_source=_int_arg(query, "limit_per_source", 50),
            full=_bool_arg(query, "full", False),
        )
    if method == "GET" and path == "/api/ecosystem/discover":
        return discover_hapa_codebases()
    if method == "GET" and path == "/api/ecosystem/ast":
        return run_hapa_ecosystem_ast_analysis(
            full=_bool_arg(query, "full", False),
            limit_per_codebase=_int_arg(query, "limit_per_codebase", 50),
            max_codebases=_optional_int_arg(query, "max_codebases"),
            output=_str_arg(query, "output", "") or None,
        )
    if method == "GET" and path == "/api/knowledge/graph":
        return run_hapa_knowledge_analysis(
            full=_bool_arg(query, "full", False),
            limit_per_source=_int_arg(query, "limit_per_source", 100),
            source_ids=query.get("source") or None,
            output=_str_arg(query, "output", "") or None,
        )
    if method == "GET" and path == "/api/writeback":
        return plan_writeback(
            target=_str_arg(query, "target", "all"),
            dry_run=_bool_arg(query, "dry_run", True),
        )

    if method == "POST" and path in {"/api/ingest/dry-run", "/api/ingest"}:
        if path == "/api/ingest" and not _body_bool(body, "dry_run", True):
            return {"ok": False, "error": "full_ingest_requires_explicit_authority"}
        return ingest_dry_run(str(body.get("source") or "all"))
    if method == "POST" and path == "/api/append":
        return append_since_last_success(dry_run=_body_bool(body, "dry_run", True))
    if method == "POST" and path == "/api/reconcile":
        return reconcile_against(
            str(body.get("against") or "second-brain"),
            dry_run=_body_bool(body, "dry_run", True),
        )
    if method == "POST" and path == "/api/export":
        return export_graph(
            source_id=str(body.get("source") or "all"),
            output=body.get("output"),
            dry_run=_body_bool(body, "dry_run", True),
            public=_body_bool(body, "public", False),
            limit_per_source=int(body.get("limit_per_source") or 50),
            full=_body_bool(body, "full", False),
        )
    if method == "POST" and path == "/api/board/checkpoint":
        message = str(body.get("message") or "").strip()
        if not message:
            return {"ok": False, "error": "message is required"}
        return board_checkpoint(message, dry_run=_body_bool(body, "dry_run", True))
    if method == "POST" and path == "/api/writeback":
        return plan_writeback(
            target=str(body.get("target") or "all"),
            dry_run=_body_bool(body, "dry_run", True),
            output=body.get("output"),
        )
    if method == "POST" and path == "/api/ecosystem/ast":
        return run_hapa_ecosystem_ast_analysis(
            full=_body_bool(body, "full", False),
            limit_per_codebase=int(body.get("limit_per_codebase") or 50),
            max_codebases=int(body["max_codebases"]) if body.get("max_codebases") is not None else None,
            output=body.get("output"),
        )
    if method == "POST" and path == "/api/knowledge/graph":
        source_ids = body.get("source_ids")
        if source_ids is not None and not isinstance(source_ids, list):
            return {"ok": False, "error": "source_ids must be a list when provided"}
        return run_hapa_knowledge_analysis(
            full=_body_bool(body, "full", False),
            limit_per_source=int(body.get("limit_per_source") or 100),
            source_ids=source_ids,
            output=body.get("output"),
        )

    return {"ok": False, "error": "not_found", "method": method, "path": path}


def run_server(host: str = "127.0.0.1", port: int = 8796) -> None:
    server = ThreadingHTTPServer((host, port), HapaGraphifyHandler)
    print(json.dumps({"ok": True, "service": "hapa-graphify-api", "host": host, "port": port}, sort_keys=True))
    try:
        server.serve_forever()
    finally:
        server.server_close()


def _str_arg(query: dict[str, list[str]], key: str, default: str) -> str:
    values = query.get(key)
    return values[0] if values else default


def _int_arg(query: dict[str, list[str]], key: str, default: int) -> int:
    try:
        return int(_str_arg(query, key, str(default)))
    except ValueError:
        return default


def _optional_int_arg(query: dict[str, list[str]], key: str) -> int | None:
    if key not in query:
        return None
    try:
        return int(_str_arg(query, key, ""))
    except ValueError:
        return None


def _bool_arg(query: dict[str, list[str]], key: str, default: bool) -> bool:
    value = _str_arg(query, key, "1" if default else "0").lower()
    return value in {"1", "true", "yes", "on"}


def _body_bool(body: dict[str, Any], key: str, default: bool) -> bool:
    value = body.get(key, default)
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes", "on"}
