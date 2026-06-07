# MCP Tools

Status: JSONL-compatible scaffold with Hapa-aware tool calls.

```bash
python3 -m hapa_graphify mcp tools --json
python3 -m hapa_graphify mcp call hapa_graph_query --args-json '{"q":"hapa-graphify","node_type":"kanban_card"}' --json
python3 -m hapa_graphify mcp call hapa_graph_path --args-json '{"start":"Build Hapa Graphify CLI parity","end":"hapa-graphify"}' --json
python3 -m hapa_graphify mcp serve-jsonl
```

## Query-First Rule

Agents must call `hapa_source_list` and then `hapa_graph_query` with filters before loading path, explain, review, export, or writeback context.

Recommended filters:

- `source_id`
- `node_type`
- `truth_status`
- `record_owner`
- `privacy`
- `limit`
- `max_nodes`

The default graph guard is `1000` nodes. If a tool returns `graph_too_large`, narrow the query or add filters. Do not bypass the guard by loading raw source files into prompts.

## Tool Names

- `hapa_source_list`
- `hapa_graph_query`
- `hapa_graph_path`
- `hapa_graph_explain`
- `hapa_review_suggestions`
- `hapa_export_dry_run`

All export/writeback-adjacent tools are dry-run/proposal-only unless a separate authorized append/write path is explicitly invoked.
