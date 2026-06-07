# CLI

Implemented commands:

```bash
python3 -m hapa_graphify health --deep --json
python3 -m hapa_graphify capabilities --json
python3 -m hapa_graphify smoke --dry-run --json
python3 -m hapa_graphify sources list --json
python3 -m hapa_graphify sources validate --json
python3 -m hapa_graphify ingest --source all --dry-run --json
python3 -m hapa_graphify fragment --source second-brain-live --limit 25 --json
python3 -m hapa_graphify ledger record-smoke --dry-run --json
python3 -m hapa_graphify ledger list --json
python3 -m hapa_graphify append --since last-success --dry-run --json
python3 -m hapa_graphify reports list --json
python3 -m hapa_graphify map --level source_type --limit 64 --edge-limit 180 --json
python3 -m hapa_graphify map --level source_type --focus-id map:source_type:... --limit 24 --edge-limit 80 --json
python3 -m hapa_graphify review-suggestions --source hapa-front-door-docs --limit 25 --json
python3 -m hapa_graphify telemetry probe --url http://127.0.0.1:8796/health --json
python3 -m hapa_graphify reconcile --against second-brain --dry-run --json
python3 -m hapa_graphify query "hapa graphify" --source all --limit-per-source 50 --node-type protocol_card --json
python3 -m hapa_graphify browse --source worldbuilding-wiki-full --query protocol --limit 25 --offset 0 --limit-per-source 80 --json
python3 -m hapa_graphify path "hapa-graphify" "hapa-second-brain" --limit-per-source 50 --json
python3 -m hapa_graphify explain "hapa-graphify" --limit-per-source 50 --json
python3 -m hapa_graphify ecosystem discover --json
python3 -m hapa_graphify ecosystem ast --max-codebases 5 --limit-per-codebase 20 --json
python3 -m hapa_graphify ecosystem ast --full --output reports/hapa-ecosystem-ast-run.json --json
python3 -m hapa_graphify knowledge graph --limit-per-source 25 --json
python3 -m hapa_graphify knowledge graph --full --output reports/hapa-knowledge-graph-run.json --json
python3 -m hapa_graphify narrative run --start-date 2026-01-01 --end-date 2026-06-07 --json
python3 -m hapa_graphify fragment --source hapa-ecosystem-codebases --full --json
python3 -m hapa_graphify export --source all --dry-run --json
python3 -m hapa_graphify export --source all --public --dry-run --json
python3 -m hapa_graphify export --source hapa-ecosystem-codebases --full --dry-run --json
python3 -m hapa_graphify board checkpoint --message "operator note" --dry-run --json
python3 -m hapa_graphify serve --host 127.0.0.1 --port 8796
python3 -m hapa_graphify mcp tools --json
python3 -m hapa_graphify mcp call hapa_graph_query --args-json '{"q":"hapa-graphify","node_type":"kanban_card"}' --json
python3 -m hapa_graphify benchmark --output reports/performance-baseline.json --json
python3 -m hapa_graphify writeback --target all --dry-run --output reports/writeback-plan.json --json
```

Write-capable commands:

```bash
hapa-graphify append --since last-success --json
hapa-graphify reconcile --against second-brain --json
hapa-graphify export --source all --output exports/graph.json --json
hapa-graphify board checkpoint --message "..." --json
```

All write-capable commands support `--dry-run`; operators and agents should run the dry-run form first and attach the JSON result as board evidence.

## Full Ecosystem AST Runbook

1. Discover Hapa codebases:

```bash
python3 -m hapa_graphify ecosystem discover --json
```

2. Run a quick bounded AST sample:

```bash
python3 -m hapa_graphify ecosystem ast --max-codebases 5 --limit-per-codebase 20 --json
```

3. Run the full Graphify AST/code analysis over every discovered Hapa codebase:

```bash
.venv/bin/python -m hapa_graphify ecosystem ast --full --output reports/hapa-ecosystem-ast-run.json --json
```

4. Attach `reports/hapa-ecosystem-ast-run.json` to the Overwatch board as evidence.

Sample mode is intentionally bounded. Full ecosystem coverage requires `--full`; otherwise Hapa Graphify caps the dynamic ecosystem source to at most ten codebases so the UI, benchmark, MCP, and API stay responsive.

## Knowledge Graph Runbook

Use this path when the target is Hapa Second Brain, Hapa wiki, protocol docs, markdown pages, Quest Keeper audits, and Overwatch board knowledge rather than source code AST:

```bash
python3 -m hapa_graphify knowledge graph --limit-per-source 25 --json
.venv/bin/python -m hapa_graphify knowledge graph --full --output reports/hapa-knowledge-graph-run.json --json
```

The full run includes the structured Second Brain tables, Hapa front-door docs, the full Hapa Worldbuilding Wiki markdown vault, wiki Operations docs, Quest Keeper audits, and the Hapa Graphify Overwatch board. Markdown pages are organized by collection, directory, article, protocol/heading nodes, and wikilinks.

## Explorer Runbook

Use `reports list` to inspect full-run evidence cheaply. It reads compact sidecar summaries instead of loading the 100MB+ report payloads:

```bash
python3 -m hapa_graphify reports list --json
```

Use `map` for high-level atlas views. It reads compact map sidecars with group nodes and weighted group-to-group edges:

```bash
python3 -m hapa_graphify map --level source_type --limit 64 --edge-limit 180 --json
python3 -m hapa_graphify map --kind code_ast --level type --limit 32 --json
```

Use `--focus-id` with a group id returned by `map` to fetch that group's connected atlas neighbors:

```bash
python3 -m hapa_graphify map --level source_type --focus-id map:source_type:f12a4fe4eea5 --limit 24 --edge-limit 80 --json
```

Use `query` for ranked lookup and `browse` for paged inspection after selecting a group. Keep `--limit-per-source` bounded during interactive work, then run the explicit full AST or full knowledge commands when you need full coverage evidence.

```bash
python3 -m hapa_graphify query "protocol" --source worldbuilding-wiki-full --node-type wiki_article --limit-per-source 80 --json
python3 -m hapa_graphify browse --source second-brain-live --limit 25 --offset 0 --limit-per-source 120 --json
```
