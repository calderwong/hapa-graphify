# Testing

Run the local CI-equivalent suite:

```bash
python3 -m compileall -q hapa_graphify
python3 -m unittest discover -s tests
python3 -m hapa_graphify smoke --dry-run --json
python3 -m hapa_graphify ecosystem discover --json
python3 -m hapa_graphify knowledge graph --limit-per-source 5 --json
python3 -m hapa_graphify export --source hapa-front-door-docs --public --dry-run --json
bin/hapa-graphify-desktop.sh --check
```

## Coverage Map

- Core health/capabilities/source validation.
- Hapa graph schema validation and golden fixture.
- Stable ID generation and Graphify node-link decoration.
- Second Brain SQLite adapter fixture.
- Hapa NODE_MAP and manifest adapter fixture.
- Wiki markdown/frontmatter/wikilink fixture.
- Repo root include/exclude fixture.
- Overwatch Kanban event fixture.
- Run ledger, incremental append, reconcile, and review suggestions.
- Telemetry loopback blocking and timestamped endpoint nodes.
- Hapa ecosystem codebase discovery fixture and loopback route.
- Knowledge graph sample route and markdown full-mode fixture.
- CLI query/path/explain/export/board checkpoint.
- Loopback API and `/ui` route smoke.
- MCP query-first tools and oversized graph guard.
- Desktop shell contract and launcher smoke.
- Public export redaction and credential path blocking.

## CI Notes

The suite has no mandatory network dependency and no required Electron install. Actual Electron window launch is optional; `bin/hapa-graphify-desktop.sh --check` verifies the desktop contract in CI.

Full ecosystem AST analysis is intentionally not part of the unit suite because it scans local Hapa codebases. Validate it manually when board work requires complete coverage:

```bash
.venv/bin/python -m hapa_graphify ecosystem ast --full --output reports/hapa-ecosystem-ast-run.json --json
```

Full knowledge graph analysis is also a local-data validation pass:

```bash
.venv/bin/python -m hapa_graphify knowledge graph --full --output reports/hapa-knowledge-graph-run.json --json
```
