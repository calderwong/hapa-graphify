# Hapa Graphify Agent Guide

This file is the repo-local operating contract for Codex, MCP clients, local automations, and Hapa agents.

## Source Truth Order

1. Live source in this repository.
2. `config/hapa-graphify.sources.json`.
3. Hapa Second Brain, Hapa wiki, Hapa front-door docs, Quest Keeper, and Overwatch sources listed in the registry.
4. Compact report sidecars under `reports/*.summary.json` and `reports/*.map.json` when present locally.
5. Upstream Graphify at the pinned reviewed commit.
6. Derived or inferred graph relationships.

If sources conflict, preserve the conflict with truth labels instead of silently collapsing it.

## Required Startup

Run these before broad graph work:

```bash
.venv/bin/python -m hapa_graphify health --deep --json
.venv/bin/python -m hapa_graphify sources validate --json
.venv/bin/python -m hapa_graphify reports list --json
```

For exploration, start with the atlas:

```bash
.venv/bin/python -m hapa_graphify map --kind all --level source_type --limit 64 --edge-limit 180 --json
```

Then narrow with `query`, `browse`, `path`, `explain`, or `map --focus-id`.

## Safe Edit Boundary

Safe by default:

- Edit this scaffold repository.
- Read source registry targets in dry-run/read-only mode.
- Generate local reports, summaries, map sidecars, and public-redacted demo data.
- Append board evidence only when explicitly authorized by a human or protocol.

Not safe without explicit authorization:

- Mutate upstream Graphify.
- Mutate Hapa Second Brain DBs, WAL/SHM files, wiki canon, source repos, node stores, generated media, credentials, or Lance indexes.
- Publish full reports, private paths, record keys, source samples, raw media, or token files.

## Query-First Rule

Use high-level and bounded surfaces before loading detail:

1. `reports list`
2. `map --kind all --level source_type`
3. `map --focus-id <group-id>` after a group click
4. `query` or `browse` with `source`, `node_type`, `truth_status`, and `limit_per_source`
5. `path` or `explain` only after narrowing

When using MCP:

1. Call `hapa_source_list`.
2. Call `hapa_graph_query` with filters.
3. Only then call `hapa_graph_path`, `hapa_graph_explain`, review suggestions, or export dry-run.

Respect `graph_too_large`; narrow filters instead of reading raw source files into prompts.

## Truth Labels

Keep these labels intact:

- `verified_source`: directly found in source material.
- `verified_runtime`: proven by local runtime or smoke check.
- `derived_or_inferred`: computed relationship.
- `needs_review`: ambiguous or conflict-prone.
- `blocked`: unavailable, missing, auth-gated, or not authorized.

## Owner Labels

Do not collapse all records into `hapa-graphify`. `record_owner` names the source of authority:

- `hapa-second-brain`
- `hapa-worldbuilding-wiki`
- `hapa-overwatch-kanban`
- `hapa-quest-keeper`
- `hapa-graphify`
- `graphify-upstream`

## Full Runs

Use explicit full commands when coverage matters:

```bash
.venv/bin/python -m hapa_graphify knowledge graph --full --output reports/hapa-knowledge-graph-run.json --json
.venv/bin/python -m hapa_graphify ecosystem ast --full --output reports/hapa-ecosystem-ast-run.json --json
```

The full report files are local-private. Public surfaces should use compact sidecars or `scripts/build_pages_demo.py`.

## Public Demo And Publishing

Before publishing:

```bash
.venv/bin/python scripts/build_pages_demo.py
.venv/bin/python -m compileall -q hapa_graphify
.venv/bin/python -m unittest discover -s tests
```

Do not stage:

- `reports/hapa-*.json` full reports.
- `runs/`.
- `graphify-out/`.
- SQLite DBs and WAL/SHM files.
- `.env`, `.node_token`, raw media, private exports, or credentials.

See `docs/PUBLISHING.md` for the release flow.

## Related Hapa Skills

Use `docs/SKILLS.md` to choose the right ecosystem skill. Common pairings:

- `hapa-board-keeper` for Overwatch/Quest Keeper board refresh and audit work.
- `hapa-flow-explainer` for wiki/protocol flow explanations.
- `hapa-turn-miner` and `hapa-turn-result-lineage` for conversation-to-knowledge lineage.
- `hapa-astros-design` when changing the operator UI aesthetic.

## Verification

```bash
.venv/bin/python -m compileall -q hapa_graphify
.venv/bin/python -m hapa_graphify smoke --dry-run --json
.venv/bin/python -m hapa_graphify mcp tools --json
.venv/bin/python -m unittest discover -s tests
```
