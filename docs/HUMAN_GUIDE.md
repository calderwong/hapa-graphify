# Human Guide

## Quick Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[graphify]"
.venv/bin/python -m hapa_graphify health --deep --json
.venv/bin/python -m hapa_graphify serve --host 127.0.0.1 --port 8796
```

Open:

```text
http://127.0.0.1:8796/ui
```

## First Screen

The UI defaults to the combined `all` atlas. That means it shows every available compact map sidecar, currently knowledge plus code AST, as a single high-level graph.

Use the atlas controls to switch views:

- `Atlas`: `all`, `knowledge`, `code_ast`, or `latest`.
- `Group By`: `source x type`, `type`, `community`, `truth`, or `owner`.
- `Groups` and `Edges`: visible atlas window limits.

## Reading The Map

- Larger nodes represent larger groups.
- Thicker edges represent more relationships between groups.
- Clicking a node loads its connected groups.
- `Drill Group` loads bounded live records for the selected group.
- `Load Map` returns to the current top-level atlas.

## Common Tasks

- **See the whole ecosystem:** Load `Atlas = all`, `Group By = source x type`.
- **Find protocol/docs clusters:** Select the wiki or protocol-card groups, then drill.
- **Inspect code structure:** Switch to `Atlas = code_ast`, `Group By = type`.
- **Search for a record:** Use `Search` after selecting a source/type/truth filter.
- **Browse records in a group:** Click a group, then use `Drill Group`.
- **Explain a node:** Select a record or paste an ID, then click `Explain`.
- **Find a path:** Fill `Path Start` and `Path End`, then click `Path`.

## Full Runs

Full runs can take time and produce large local-private reports:

```bash
.venv/bin/python -m hapa_graphify ecosystem ast --full --output reports/hapa-ecosystem-ast-run.json --json
.venv/bin/python -m hapa_graphify knowledge graph --full --output reports/hapa-knowledge-graph-run.json --json
```

After a full run, Hapa Graphify writes compact sidecars next to the report. The UI and GitHub Pages demo should use those compact sidecars, not the full reports.

## Safety

The default is read-only and local-first. Write-capable commands support dry-run first and should not mutate Hapa Second Brain, wiki, Overwatch, Lance, or source repos without explicit authorization.
