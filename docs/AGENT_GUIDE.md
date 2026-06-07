# Agent Guide

This guide is for Codex, MCP clients, local automations, and other Hapa agents.

## Required Operating Rules

1. Start with `health --deep` and `sources validate`.
2. Treat source registry targets as read-only unless an explicit write protocol grants authority.
3. Use atlas or query routes before loading detailed context.
4. Honor privacy labels and truth status.
5. Use dry-run before append, reconcile, export, board checkpoint, or writeback.
6. Do not read private raw folders, token files, WAL/SHM files, `.env`, `.git`, `node_modules`, or generated private media into prompts or public exports.

## Recommended Agent Flow

```bash
.venv/bin/python -m hapa_graphify health --deep --json
.venv/bin/python -m hapa_graphify sources validate --json
.venv/bin/python -m hapa_graphify reports list --json
.venv/bin/python -m hapa_graphify map --level source_type --limit 64 --edge-limit 180 --json
```

Then narrow:

```bash
.venv/bin/python -m hapa_graphify map --level source_type --focus-id <group-id> --json
.venv/bin/python -m hapa_graphify query "protocol" --source worldbuilding-wiki-full --limit-per-source 80 --json
.venv/bin/python -m hapa_graphify browse --source second-brain-live --limit 25 --offset 0 --json
```

## MCP Query-First Rule

When using MCP:

1. Call `hapa_source_list`.
2. Call `hapa_graph_query` with filters.
3. Only then call `hapa_graph_path`, `hapa_graph_explain`, review suggestions, or export dry-run.

If a tool returns `graph_too_large`, add filters instead of bypassing the guard.

## Truth Status

- `verified_source`: directly found in source material.
- `verified_runtime`: proven by local runtime or smoke check.
- `derived_or_inferred`: computed relationship.
- `needs_review`: ambiguous or conflict-prone.
- `blocked`: unavailable, missing, auth-gated, or not authorized.

## Owner Labels

Keep `record_owner` stable. Do not collapse all records into `hapa-graphify`; the owner identifies the source of authority:

- `hapa-second-brain`
- `hapa-worldbuilding-wiki`
- `hapa-overwatch-kanban`
- `hapa-quest-keeper`
- `hapa-graphify`
- `graphify-upstream`

## Write And Publish Rules

Write-capable commands are proposal surfaces unless explicitly authorized:

```bash
.venv/bin/python -m hapa_graphify export --source all --public --dry-run --json
.venv/bin/python -m hapa_graphify writeback --target all --dry-run --json
.venv/bin/python -m hapa_graphify board checkpoint --message "..." --dry-run --json
```

Only publish public-safe derived artifacts. Full reports, run ledgers, local source registries with absolute paths, and graph outputs are local-private by default.
