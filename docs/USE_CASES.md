# Use Cases

## 1. Understand The Whole Hapa Ecosystem

Use `Atlas = all` and `Group By = source x type` in the UI, or:

```bash
.venv/bin/python -m hapa_graphify map --level source_type --json
```

This shows knowledge, wiki, docs, board, and code AST groups together.

## 2. Inspect A Community

Click a group in the map. The UI loads connected groups with weighted edges. From there, use `Drill Group` to load bounded records.

CLI equivalent:

```bash
.venv/bin/python -m hapa_graphify map --level source_type --focus-id <group-id> --json
```

## 3. Explore Protocol Documentation

Start with the all atlas, find wiki/protocol groups, then drill. Use query for exact text:

```bash
.venv/bin/python -m hapa_graphify query "protocol" --source worldbuilding-wiki-full --limit-per-source 80 --json
```

## 4. Discover Codebase Structure

Run:

```bash
.venv/bin/python -m hapa_graphify ecosystem discover --json
.venv/bin/python -m hapa_graphify ecosystem ast --max-codebases 5 --limit-per-codebase 20 --json
```

Use full AST only when you need full evidence:

```bash
.venv/bin/python -m hapa_graphify ecosystem ast --full --output reports/hapa-ecosystem-ast-run.json --json
```

## 5. Build A Knowledge Graph From Second Brain And Wiki

Run:

```bash
.venv/bin/python -m hapa_graphify knowledge graph --limit-per-source 25 --json
.venv/bin/python -m hapa_graphify knowledge graph --full --output reports/hapa-knowledge-graph-run.json --json
```

## 6. Prepare Public-Redacted Outputs

Run:

```bash
.venv/bin/python -m hapa_graphify export --source all --public --dry-run --json
.venv/bin/python -m hapa_graphify writeback --target all --dry-run --json
```

Use dry-run output as review evidence before any authorized write.

## 7. Agent Retrieval Prep

Agents should start with:

```bash
.venv/bin/python -m hapa_graphify map --level source_type --json
.venv/bin/python -m hapa_graphify query "<topic>" --source all --limit-per-source 50 --json
```

Then use `explain`, `path`, or MCP tools only after narrowing context.

## 8. Board Evidence And Review Suggestions

Run:

```bash
.venv/bin/python -m hapa_graphify review-suggestions --source hapa-front-door-docs --json
.venv/bin/python -m hapa_graphify board checkpoint --message "Validated graph atlas docs" --dry-run --json
```

Board writes stay dry-run unless a human or authorized board protocol grants append authority.
