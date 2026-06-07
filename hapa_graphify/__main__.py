from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys

from .api import run_server
from .benchmark import run_benchmark
from .core import (
    board_checkpoint,
    browse_graph_nodes,
    build_source_fragment,
    capabilities,
    append_since_last_success,
    discover_hapa_codebases,
    explain_graph_node,
    export_graph,
    graph_group_neighbors,
    graph_overview,
    health,
    ingest_dry_run,
    list_ledger_entries,
    list_sources,
    path_between,
    query_graph,
    record_smoke_run,
    reconcile_against,
    report_summaries,
    review_suggestions_for_source,
    run_hapa_ecosystem_ast_analysis,
    run_hapa_knowledge_analysis,
    smoke,
    telemetry_probe,
    validate_sources,
)
from .mcp import call_mcp_tool, list_mcp_tools, run_jsonl_server
from .narrative import run_narrative_agent
from .writeback import plan_writeback


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="hapa-graphify")
    sub = parser.add_subparsers(dest="command", required=True)

    p_health = sub.add_parser("health")
    p_health.add_argument("--deep", action="store_true")
    p_health.add_argument("--json", action="store_true")

    p_caps = sub.add_parser("capabilities")
    p_caps.add_argument("--json", action="store_true")

    p_smoke = sub.add_parser("smoke")
    p_smoke.add_argument("--dry-run", action="store_true")
    p_smoke.add_argument("--json", action="store_true")

    p_sources = sub.add_parser("sources")
    p_sources.add_argument("action", choices=["list", "validate"])
    p_sources.add_argument("--json", action="store_true")

    p_ingest = sub.add_parser("ingest")
    p_ingest.add_argument("--source", default="all")
    p_ingest.add_argument("--dry-run", action="store_true")
    p_ingest.add_argument("--json", action="store_true")

    p_fragment = sub.add_parser("fragment")
    p_fragment.add_argument("--source", required=True)
    p_fragment.add_argument("--limit", type=int, default=100)
    p_fragment.add_argument("--full", action="store_true")
    p_fragment.add_argument("--max-codebases", type=int)
    p_fragment.add_argument("--json", action="store_true")

    p_ledger = sub.add_parser("ledger")
    p_ledger.add_argument("action", choices=["record-smoke", "list"])
    p_ledger.add_argument("--dry-run", action="store_true")
    p_ledger.add_argument("--limit", type=int, default=20)
    p_ledger.add_argument("--json", action="store_true")

    p_append = sub.add_parser("append")
    p_append.add_argument("--since", default="last-success")
    p_append.add_argument("--dry-run", action="store_true")
    p_append.add_argument("--json", action="store_true")

    p_reports = sub.add_parser("reports")
    p_reports.add_argument("action", choices=["list"])
    p_reports.add_argument("--json", action="store_true")

    p_map = sub.add_parser("map")
    p_map.add_argument("--kind", default="all")
    p_map.add_argument("--level", default="community", choices=["community", "type", "source_type", "truth", "owner"])
    p_map.add_argument("--limit", type=int, default=80)
    p_map.add_argument("--edge-limit", type=int, default=220)
    p_map.add_argument("--focus-id")
    p_map.add_argument("--json", action="store_true")

    p_reconcile = sub.add_parser("reconcile")
    p_reconcile.add_argument("--against", default="second-brain")
    p_reconcile.add_argument("--dry-run", action="store_true")
    p_reconcile.add_argument("--json", action="store_true")

    p_query = sub.add_parser("query")
    p_query.add_argument("query")
    p_query.add_argument("--source", default="all")
    p_query.add_argument("--limit", type=int, default=20)
    p_query.add_argument("--limit-per-source", type=int, default=50)
    p_query.add_argument("--node-type")
    p_query.add_argument("--truth-status")
    p_query.add_argument("--json", action="store_true")

    p_browse = sub.add_parser("browse")
    p_browse.add_argument("--source", default="all")
    p_browse.add_argument("--query", default="")
    p_browse.add_argument("--limit", type=int, default=50)
    p_browse.add_argument("--offset", type=int, default=0)
    p_browse.add_argument("--limit-per-source", type=int)
    p_browse.add_argument("--node-type")
    p_browse.add_argument("--truth-status")
    p_browse.add_argument("--json", action="store_true")

    p_path = sub.add_parser("path")
    p_path.add_argument("start")
    p_path.add_argument("end")
    p_path.add_argument("--source", default="all")
    p_path.add_argument("--max-depth", type=int, default=6)
    p_path.add_argument("--limit-per-source", type=int, default=50)
    p_path.add_argument("--json", action="store_true")

    p_explain = sub.add_parser("explain")
    p_explain.add_argument("identifier")
    p_explain.add_argument("--source", default="all")
    p_explain.add_argument("--limit-per-source", type=int, default=50)
    p_explain.add_argument("--json", action="store_true")

    p_export = sub.add_parser("export")
    p_export.add_argument("--source", default="all")
    p_export.add_argument("--output")
    p_export.add_argument("--dry-run", action="store_true")
    p_export.add_argument("--public", action="store_true")
    p_export.add_argument("--limit-per-source", type=int, default=50)
    p_export.add_argument("--full", action="store_true")
    p_export.add_argument("--json", action="store_true")

    p_board = sub.add_parser("board")
    p_board.add_argument("action", choices=["checkpoint"])
    p_board.add_argument("--message", required=True)
    p_board.add_argument("--dry-run", action="store_true")
    p_board.add_argument("--json", action="store_true")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8796)

    p_mcp = sub.add_parser("mcp")
    p_mcp.add_argument("action", choices=["tools", "call", "serve-jsonl"])
    p_mcp.add_argument("tool", nargs="?")
    p_mcp.add_argument("--args-json", default="{}")
    p_mcp.add_argument("--json", action="store_true")

    p_benchmark = sub.add_parser("benchmark")
    p_benchmark.add_argument("--output")
    p_benchmark.add_argument("--limit-per-source", type=int, default=50)
    p_benchmark.add_argument("--json", action="store_true")

    p_writeback = sub.add_parser("writeback")
    p_writeback.add_argument("--target", default="all")
    p_writeback.add_argument("--dry-run", action="store_true")
    p_writeback.add_argument("--output")
    p_writeback.add_argument("--json", action="store_true")

    p_review = sub.add_parser("review-suggestions")
    p_review.add_argument("--source", required=True)
    p_review.add_argument("--limit", type=int, default=100)
    p_review.add_argument("--json", action="store_true")

    p_telemetry = sub.add_parser("telemetry")
    p_telemetry.add_argument("action", choices=["probe"])
    p_telemetry.add_argument("--url", action="append", default=[])
    p_telemetry.add_argument("--json", action="store_true")

    p_ecosystem = sub.add_parser("ecosystem")
    p_ecosystem.add_argument("action", choices=["discover", "ast"])
    p_ecosystem.add_argument("--full", action="store_true")
    p_ecosystem.add_argument("--limit-per-codebase", type=int, default=50)
    p_ecosystem.add_argument("--max-codebases", type=int)
    p_ecosystem.add_argument("--output")
    p_ecosystem.add_argument("--json", action="store_true")

    p_knowledge = sub.add_parser("knowledge")
    p_knowledge.add_argument("action", choices=["graph"])
    p_knowledge.add_argument("--full", action="store_true")
    p_knowledge.add_argument("--limit-per-source", type=int, default=100)
    p_knowledge.add_argument("--source", action="append", default=[])
    p_knowledge.add_argument("--output")
    p_knowledge.add_argument("--json", action="store_true")

    p_narrative = sub.add_parser("narrative")
    p_narrative.add_argument("action", choices=["run"])
    p_narrative.add_argument("--start-date", default="2026-01-01")
    p_narrative.add_argument("--end-date", default="2026-06-07")
    p_narrative.add_argument("--output")
    p_narrative.add_argument("--run-log")
    p_narrative.add_argument("--image-queue")
    p_narrative.add_argument("--generate-images", action="store_true")
    p_narrative.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "health":
        result = health(deep=args.deep)
    elif args.command == "capabilities":
        result = capabilities()
    elif args.command == "smoke":
        result = smoke(dry_run=args.dry_run)
    elif args.command == "sources":
        result = list_sources() if args.action == "list" else validate_sources()
    elif args.command == "ingest":
        if not args.dry_run:
            result = {"ok": False, "error": "Only --dry-run ingest is implemented in this scaffold."}
        else:
            result = ingest_dry_run(args.source)
    elif args.command == "fragment":
        result = build_source_fragment(
            args.source,
            limit_per_table=0 if args.full else args.limit,
            full=args.full,
            max_codebases=args.max_codebases,
        )
    elif args.command == "ledger":
        if args.action == "record-smoke":
            result = record_smoke_run(dry_run=args.dry_run)
        else:
            result = list_ledger_entries(limit=args.limit)
    elif args.command == "append":
        if args.since != "last-success":
            result = {"ok": False, "error": "Only --since last-success is implemented."}
        else:
            result = append_since_last_success(dry_run=args.dry_run)
    elif args.command == "reports":
        result = report_summaries()
    elif args.command == "map":
        if args.focus_id:
            result = graph_group_neighbors(
                args.focus_id,
                kind=args.kind,
                level=args.level,
                limit=args.limit,
                edge_limit=args.edge_limit,
            )
        else:
            result = graph_overview(
                kind=args.kind,
                level=args.level,
                limit=args.limit,
                edge_limit=args.edge_limit,
            )
    elif args.command == "reconcile":
        result = reconcile_against(args.against, dry_run=args.dry_run)
    elif args.command == "query":
        result = query_graph(
            args.query,
            source_id=args.source,
            limit=args.limit,
            limit_per_source=args.limit_per_source,
            node_type=args.node_type,
            truth_status=args.truth_status,
        )
    elif args.command == "browse":
        result = browse_graph_nodes(
            source_id=args.source,
            query=args.query,
            limit=args.limit,
            offset=args.offset,
            limit_per_source=args.limit_per_source,
            node_type=args.node_type,
            truth_status=args.truth_status,
        )
    elif args.command == "path":
        result = path_between(
            args.start,
            args.end,
            source_id=args.source,
            max_depth=args.max_depth,
            limit_per_source=args.limit_per_source,
        )
    elif args.command == "explain":
        result = explain_graph_node(
            args.identifier,
            source_id=args.source,
            limit_per_source=args.limit_per_source,
        )
    elif args.command == "export":
        result = export_graph(
            source_id=args.source,
            output=args.output,
            dry_run=args.dry_run,
            public=args.public,
            limit_per_source=0 if args.full else args.limit_per_source,
            full=args.full,
        )
    elif args.command == "board":
        result = board_checkpoint(args.message, dry_run=args.dry_run)
    elif args.command == "serve":
        run_server(host=args.host, port=args.port)
        return 0
    elif args.command == "mcp":
        if args.action == "tools":
            result = list_mcp_tools()
        elif args.action == "call":
            if not args.tool:
                result = {"ok": False, "error": "tool is required"}
            else:
                try:
                    tool_args = json.loads(args.args_json)
                except json.JSONDecodeError as exc:
                    result = {"ok": False, "error": f"invalid args json: {exc}"}
                else:
                    result = call_mcp_tool(args.tool, tool_args)
        else:
            run_jsonl_server()
            return 0
    elif args.command == "benchmark":
        result = run_benchmark(output=args.output, limit_per_source=args.limit_per_source)
    elif args.command == "writeback":
        result = plan_writeback(target=args.target, dry_run=args.dry_run, output=args.output)
    elif args.command == "review-suggestions":
        result = review_suggestions_for_source(args.source, limit_per_table=args.limit)
    elif args.command == "telemetry":
        result = telemetry_probe(args.url or None)
    elif args.command == "ecosystem":
        if args.action == "discover":
            result = discover_hapa_codebases()
        else:
            result = run_hapa_ecosystem_ast_analysis(
                full=args.full,
                limit_per_codebase=args.limit_per_codebase,
                max_codebases=args.max_codebases,
                output=args.output,
            )
    elif args.command == "knowledge":
        result = run_hapa_knowledge_analysis(
            full=args.full,
            limit_per_source=args.limit_per_source,
            source_ids=args.source or None,
            output=args.output,
        )
    elif args.command == "narrative":
        result = run_narrative_agent(
            start_date=date.fromisoformat(args.start_date),
            end_date=date.fromisoformat(args.end_date),
            output=Path(args.output) if args.output else None,
            run_log=Path(args.run_log) if args.run_log else None,
            image_queue=Path(args.image_queue) if args.image_queue else None,
            generate_images=args.generate_images,
        )
    else:  # pragma: no cover
        result = {"ok": False, "error": f"Unknown command {args.command}"}

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
