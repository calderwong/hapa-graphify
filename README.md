# Hapa Graphify

`hapa-graphify` is the local-first graph compiler and explorer for the Hapa ecosystem. It adapts the reviewed upstream Graphify engine into Hapa protocol terms: source owners, truth status, privacy labels, append-only evidence, UI/API/CLI/MCP/Desktop parity, and public-safe graph summaries.

It is meant to answer questions like:

- What Hapa nodes, repos, protocols, docs, skills, boards, and memory systems exist?
- How are Second Brain, wiki, Overwatch, Quest Keeper, codebases, and protocol docs connected?
- Which graph facts are verified source, runtime-verified, inferred, blocked, or review-needed?
- How can humans and agents explore the whole ecosystem without loading hundreds of thousands of records at once?

Current local full-run evidence:

- Combined atlas: `371,430` nodes and `582,209` edges.
- Knowledge graph: `309,795` nodes and `422,384` edges.
- Ecosystem AST graph: `61,635` nodes and `159,825` edges.

Full reports stay local-private. Public demos use sanitized atlas data generated from compact sidecars.

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[graphify,images]"
.venv/bin/python -m hapa_graphify health --deep --json
.venv/bin/python -m hapa_graphify sources validate --json
.venv/bin/python -m hapa_graphify serve --host 127.0.0.1 --port 8796
```

Open:

```text
http://127.0.0.1:8796/ui
```

The UI defaults to the combined `all` atlas. Start there, click a group to load its connected groups, then drill into bounded records.

## Configure Hapa Sources

The public registry uses environment-variable roots. Copy `.env.example` into your local shell/profile or export the variables directly:

```bash
export HAPA_SECOND_BRAIN_DB="/path/to/hapa_second_brain.db"
export HAPA_WIKI_ROOT="/path/to/Hapa_Worldbuilding_Wiki"
export HAPA_FRONT_DOOR_DOCS="/path/to/hapa/docs"
export HAPA_OVERWATCH_ROOT="/path/to/hapa-overwatch-kanban"
export HAPA_QUEST_KEEPER_AUDIT_ROOT="/path/to/hapa-quest-keeper/artifacts/audit"
```

Then validate:

```bash
.venv/bin/python -m hapa_graphify sources validate --json
```

## Main Access Points

- **UI:** `http://127.0.0.1:8796/ui`
- **CLI:** `.venv/bin/python -m hapa_graphify ...`
- **API:** loopback routes under `/api/*`
- **MCP:** `.venv/bin/python -m hapa_graphify mcp serve-jsonl`
- **Desktop:** `bin/hapa-graphify-desktop.sh`
- **Narrative app:** `docs/narrative/index.html`
- **Static demo:** `docs/index.html` and `docs/demo/index.html`

See [docs/ACCESS_POINTS.md](docs/ACCESS_POINTS.md) for the complete map.

## Common Runs

```bash
.venv/bin/python -m hapa_graphify reports list --json
.venv/bin/python -m hapa_graphify map --kind all --level source_type --limit 64 --edge-limit 180 --json
.venv/bin/python -m hapa_graphify query "protocol" --source all --limit-per-source 80 --json
.venv/bin/python -m hapa_graphify ecosystem discover --json
.venv/bin/python -m hapa_graphify knowledge graph --limit-per-source 25 --json
.venv/bin/python -m hapa_graphify ecosystem ast --max-codebases 5 --limit-per-codebase 20 --json
.venv/bin/python -m hapa_graphify narrative run --start-date 2026-01-01 --end-date 2026-06-07 --json
.venv/bin/python -m hapa_graphify narrative enrich --json
```

Full coverage runs:

```bash
.venv/bin/python -m hapa_graphify knowledge graph --full --output reports/hapa-knowledge-graph-run.json --json
.venv/bin/python -m hapa_graphify ecosystem ast --full --output reports/hapa-ecosystem-ast-run.json --json
```

These produce large local-private reports plus compact `*.summary.json` and `*.map.json` sidecars. The UI and public demo use the compact sidecars.

## Public Demo

Generate sanitized Pages data:

```bash
.venv/bin/python scripts/build_pages_demo.py
```

The generator writes `docs/demo-data/atlas.json` with private paths, record keys, source files, and samples omitted. Publish GitHub Pages from `docs/`.

## Documentation

- [Overview](docs/OVERVIEW.md)
- [Human Guide](docs/HUMAN_GUIDE.md)
- [Agent Guide](docs/AGENT_GUIDE.md)
- [Hapa Ecosystem Context](docs/HAPA_ECOSYSTEM.md)
- [Hapa Skills Map](docs/SKILLS.md)
- [Use Cases](docs/USE_CASES.md)
- [Hapa Narrative](docs/NARRATIVE.md)
- [Access Points](docs/ACCESS_POINTS.md)
- [CLI](docs/CLI.md)
- [API](docs/API.md)
- [MCP](docs/MCP.md)
- [Desktop](docs/DESKTOP.md)
- [Performance](docs/PERFORMANCE.md)
- [Testing](docs/TESTING.md)
- [Publishing](docs/PUBLISHING.md)
- [Threat Model](docs/THREAT_MODEL.md)
- [Data Boundary](docs/DATA_BOUNDARY.md)
- [Writeback](docs/WRITEBACK.md)
- [Feature Parity](docs/FEATURE_PARITY.md)
- [Protocol](docs/protocol/HAPA_GRAPHIFY_PROTOCOL.md)

## Source Reviewed

- Upstream: `safishamsi/graphify`
- Reviewed version: `v0.8.33`
- Reviewed commit: `4b06fd7bf7e1e407d8acb4dd9a1404e21cf34bce`
- Strategy: wrap `graphifyy` as an optional pinned engine first, then add Hapa adapters and provenance decorators around it.

## Hapa Contract

The canonical implementation spine is `hapa_graphify/core.py`. CLI, API, UI, MCP, and desktop surfaces call the same functions rather than reimplementing ingest, query, map, export, or writeback behavior.

Record owners stay with their source-of-truth systems:

- `hapa-second-brain`: memory rows, wiki article indexing, capability bridges, retrieval context.
- `hapa-worldbuilding-wiki`: durable protocol and markdown canon.
- `hapa-overwatch-kanban`: append-only task, blocker, checkpoint, and review evidence.
- `hapa-quest-keeper`: audits and node status evidence.
- `hapa-lance-node`: retrieval projections and index exports.
- `hapa-graphify`: source registry, graph compilation runs, graph deltas, local graph outputs.

Overwatch project id: `hapa-app-hapa-graphify`.
