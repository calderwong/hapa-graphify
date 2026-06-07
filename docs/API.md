# API

Status: implemented loopback scaffold over the same core spine as the CLI.

Launch:

```bash
python3 -m hapa_graphify serve --host 127.0.0.1 --port 8796
```

Implemented loopback endpoints:

- `GET /ui`
- `GET /health`
- `GET /capabilities`
- `GET /api/smoke?dry_run=1`
- `GET /api/sources`
- `GET /api/runs`
- `GET /api/reports`
- `GET /api/map?kind=all&level=source_type&limit=64&edge_limit=180`
- `GET /api/map/neighbors?kind=all&level=source_type&id=&limit=24&edge_limit=80`
- `GET /api/fragment?source=second-brain-live&limit=25`
- `POST /api/ingest/dry-run`
- `POST /api/ingest`
- `GET /api/append?dry_run=1`
- `POST /api/append`
- `GET /api/reconcile?against=second-brain&dry_run=1`
- `POST /api/reconcile`
- `GET /api/query?q=&graph_source=all&limit=20&limit_per_source=50&node_type=&truth_status=`
- `GET /api/browse?source=all&q=&limit=50&offset=0&limit_per_source=50&node_type=&truth_status=`
- `GET /api/path?source=&target=&graph_source=all&max_depth=6&limit_per_source=50`
- `GET /api/explain?id=&graph_source=all&limit_per_source=50`
- `GET /api/export?source=all&dry_run=1&public=1`
- `GET /api/ecosystem/discover`
- `GET /api/ecosystem/ast?full=1&limit_per_codebase=50&output=reports/hapa-ecosystem-ast-run.json`
- `GET /api/knowledge/graph?full=1&output=reports/hapa-knowledge-graph-run.json`
- `GET /api/writeback?target=all&dry_run=1`
- `POST /api/writeback`
- `POST /api/export`
- `POST /api/ecosystem/ast`
- `POST /api/knowledge/graph`
- `GET /api/review-suggestions?source=hapa-front-door-docs`
- `GET /api/telemetry/probe?url=http://127.0.0.1:8796/health`
- `POST /api/board/checkpoint`

Write endpoints must accept `dry_run`, return `run_id`, preserve source signatures, and include board evidence metadata.

Non-dry-run ingest is authority-gated. Agents should call the dry-run route first, attach the response as board evidence, and only append/write when a human or authorized protocol grants that action.

## Explorer Routes

Use `/api/reports` to load full-run evidence without opening the large report JSON files in the browser. Full AST and knowledge runs write compact `*.summary.json` sidecars with counts, validation status, output paths, file sizes, and per-source rollups.

Use `/api/map` for high-level atlas views. It reads compact `*.map.json` sidecars and returns group nodes plus weighted group-to-group edges for `community`, `type`, `source_type`, `truth`, and `owner` levels. The default `kind=all` combines every available map sidecar, such as knowledge and code AST, into one atlas.

Use `/api/map/neighbors` when a user clicks an atlas group. It returns an ego graph with the selected group, its top connected groups, and weighted connecting edges, so the UI can pivot from overview to local neighborhood without loading the full report.

Use `/api/query` for targeted search and `/api/browse` for paged inspection after selecting a group. Both routes build a bounded graph sample with `limit_per_source` and support `node_type` plus `truth_status` filters, so the UI can drill into the full Hapa ecosystem interactively without rendering the 300k+ node knowledge graph at once.

## Full Ecosystem AST

Use `GET /api/ecosystem/discover` to list every currently discoverable Hapa node root and codebase. Use `POST /api/ecosystem/ast` for the full run:

```json
{
  "full": true,
  "limit_per_codebase": 50,
  "output": "reports/hapa-ecosystem-ast-run.json"
}
```

Without `full=true`, ecosystem AST calls are bounded samples. The server process must run in an environment where the optional Graphify AST dependencies are importable.

## Knowledge Graph

Use `GET /api/knowledge/graph` or `POST /api/knowledge/graph` for Hapa Second Brain and wiki/protocol/documentation organization.

```json
{
  "full": true,
  "limit_per_source": 100,
  "output": "reports/hapa-knowledge-graph-run.json"
}
```

This route excludes the code AST source and focuses on Second Brain structured tables, markdown pages, folder/category structure, protocol headings, wikilinks, Quest Keeper audits, and Overwatch board knowledge.
