# Access Points

Hapa Graphify keeps one implementation spine and exposes it through several surfaces.

## CLI

Primary local automation surface:

```bash
.venv/bin/python -m hapa_graphify health --deep --json
.venv/bin/python -m hapa_graphify map --level source_type --json
.venv/bin/python -m hapa_graphify query "hapa graphify" --json
.venv/bin/python -m hapa_graphify narrative run --start-date 2026-01-01 --end-date 2026-06-07 --json
.venv/bin/python -m hapa_graphify narrative enrich --json
```

Use the CLI for scripts, tests, full runs, report generation, and agent-safe dry-run workflows.

## API

Loopback service:

```bash
.venv/bin/python -m hapa_graphify serve --host 127.0.0.1 --port 8796
```

Important routes:

- `/health`
- `/capabilities`
- `/api/sources`
- `/api/reports`
- `/api/map`
- `/api/map/neighbors`
- `/api/query`
- `/api/browse`
- `/api/path`
- `/api/explain`
- `/api/ecosystem/ast`
- `/api/knowledge/graph`
- `/api/export`
- `/api/writeback`

## UI

Open:

```text
http://127.0.0.1:8796/ui
```

Use the UI for map-first exploration, group drill-down, source filtering, path/explain, full-run launch, and dry-run export/review/checkpoint workflows.

## MCP

JSONL-compatible local tool scaffold:

```bash
.venv/bin/python -m hapa_graphify mcp tools --json
.venv/bin/python -m hapa_graphify mcp serve-jsonl
```

Use MCP for agent workflows where the client must query before loading context.

## Desktop

Electron shell scaffold:

```bash
bin/hapa-graphify-desktop.sh --check
bin/hapa-graphify-desktop.sh
```

The desktop shell starts the same loopback API and loads the same `/ui` surface.

## Skills

Hapa skills are not a separate Hapa Graphify runtime surface, but agents should use them when work crosses into board operations, wiki protocols, turn mining, result lineage, artifact flows, or Hapa UI design.

See `docs/SKILLS.md`.

## GitHub Pages Demo

The Pages demo is static and public-safe. It uses `docs/demo-data/atlas.json`, generated from compact local sidecars with private paths and samples removed.

Regenerate:

```bash
.venv/bin/python scripts/build_pages_demo.py
```
