# Hapa Graphify Overview

Hapa Graphify is the local-first graph compiler for the Hapa ecosystem. It adapts the reviewed upstream Graphify engine into Hapa protocol terms: source owners, truth status, privacy labels, append-only evidence, UI/API/CLI/MCP parity, and publish-safe summaries.

## What It Contains

- A Python core spine in `hapa_graphify/core.py`.
- CLI commands through `python3 -m hapa_graphify` and the `hapa-graphify` console script.
- A loopback HTTP API and operator UI at `/ui`.
- A JSONL MCP scaffold for agent tool use.
- An Electron desktop shell scaffold.
- Source registry adapters for SQLite, markdown roots, repo roots, Hapa ecosystem codebases, Overwatch Kanban, and telemetry probes.
- Compact report sidecars:
  - `*.summary.json` for full-run evidence.
  - `*.map.json` for atlas/community exploration.
- Public-safe GitHub Pages demo data generated from local sidecars.

## Mental Model

Hapa Graphify has three layers:

1. **Source adapters** read Hapa sources without mutating them.
2. **Graph compiler** emits typed nodes and edges with provenance, truth status, owner, and privacy metadata.
3. **Explorer surfaces** let humans and agents inspect high-level groups first, then drill into bounded live data.

The high-level atlas view is the normal starting point. Query and browse are drill-down tools, not the primary way to understand the whole system.

## Current Full-Run Evidence

The latest local full runs produced:

- Knowledge graph: `309,795` nodes and `422,384` edges.
- Ecosystem AST graph: `61,635` nodes and `159,825` edges.
- Combined atlas default: `371,430` nodes and `582,209` edges.

The full JSON reports are local-private and intentionally excluded from git. Public docs and demos use compact, redacted derivatives.

## Audience

- **Humans** use the UI, CLI, docs, and desktop shell to understand and operate Hapa graph workflows.
- **Agents** use the agent guide, MCP/query-first rules, source registry, and dry-run surfaces to interact safely.
- **Maintainers** use the tests, feature parity matrix, and publishing guide to keep the repo shippable.
