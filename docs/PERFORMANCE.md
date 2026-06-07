# Performance

Run:

```bash
python3 -m hapa_graphify benchmark --output reports/performance-baseline.json --json
```

The benchmark measures:

- Combined graph build.
- Query latency for `hapa-graphify`.
- Path lookup from the CLI parity card to the Hapa Graphify node.
- Public export dry-run.
- MCP oversized graph guard.

## UI Strategy

The operator UI renders atlas sidecars and bounded drill windows, not the whole ecosystem graph. Defaults:

- Atlas group limit: `64`.
- Atlas edge limit: `180`.
- Drill result limit: `24`.
- Detail SVG render limit: `32`.
- Report atlas: reads compact `reports/*.summary.json` sidecars for full-run counts and validation state.
- Map atlas: reads compact `reports/*.map.json` sidecars for communities, types, source/type groups, truth states, owners, and weighted group connections.
- Browse/search: builds bounded samples with `limit_per_source` after a user chooses a group.
- Path/explain: uses the same bounded sample knob before graph traversal.
- Use the inspector for detail rather than adding every adjacent node to the canvas.

## Guard Strategy

MCP tools default to `1000` max nodes. When the filtered graph exceeds the guard, tools return `graph_too_large` and a narrowing hint.

## Current Baseline

Generate `reports/performance-baseline.json` after significant adapter, query, export, UI, or MCP changes and link the report in board evidence.

The dynamic Hapa ecosystem source uses bounded sample mode in routine graph builds. Sample mode scans at most ten codebases unless `max_codebases` is lower. Full coverage is reserved for explicit runs:

```bash
.venv/bin/python -m hapa_graphify ecosystem ast --full --output reports/hapa-ecosystem-ast-run.json --json
```

Latest full run, generated on 2026-06-06 at `reports/hapa-ecosystem-ast-run.json`: 59 Hapa node roots, 74 discovered codebases, 2,981 selected code files, 61,417 graph nodes, 159,206 graph edges, zero AST errors, and schema validation OK.

Latest full knowledge run, generated on 2026-06-06 at `reports/hapa-knowledge-graph-run.json`: Second Brain plus Hapa docs/wiki/protocol/board sources produced 309,795 graph nodes and 422,384 graph edges with schema validation OK. The full wiki source contributed 56,862 markdown pages, 425 directory nodes, 195,786 heading nodes, and 146,042 wikilink edges. Privacy/path scan found 0 Raw, Private, `.git`, `node_modules`, WAL/SHM, env, or token source-file leaks.
