# Hapa Ecosystem Context

Hapa Graphify is not the source of truth for the whole Hapa ecosystem. It is the graph compiler and explorer that reads source-of-truth systems and emits typed, provenance-preserving graph projections.

## Source Systems

| Source | Graphify source id | Role | Default authority |
| --- | --- | --- | --- |
| Upstream Graphify | `graphify-upstream-reviewed` | Reviewed generic graph engine reference | read-only |
| Hapa Second Brain | `second-brain-live` | Memory rows, node registry, turns, skills, connections | read-only |
| Hapa front-door docs | `hapa-front-door-docs` | Protocol and node documentation | read-only |
| Hapa Worldbuilding Wiki | `worldbuilding-wiki-full` | Durable markdown canon, headings, wikilinks, protocol docs | read-only |
| Wiki operations docs | `worldbuilding-wiki-operations` | Operational protocol subset | read-only |
| Overwatch Kanban | `overwatch-kanban-hapa-graphify` | Board events, tasks, blockers, checkpoints | append-only events |
| Quest Keeper | `quest-keeper-audits` | Node audit and kanban audit evidence | read-only |
| Hapa codebases | `hapa-ecosystem-codebases` | Discovered repositories and AST/code graph | read-only |

The registry uses environment-variable roots such as `HAPA_SECOND_BRAIN_DB`, `HAPA_WIKI_ROOT`, `HAPA_FRONT_DOOR_DOCS`, `HAPA_OVERWATCH_ROOT`, `HAPA_QUEST_KEEPER_AUDIT_ROOT`, and `HAPA_NODE_MAP`. See `.env.example` for the local configuration shape.

## Related Hapa Nodes

- `hapa-second-brain`: structured local memory and retrieval records.
- `hapa-lance-node`: vector/retrieval projection target.
- `hapa-overwatch-kanban`: append-only project/task evidence.
- `hapa-quest-keeper`: audits and node status evidence.
- `hapa-worldbuilding-wiki`: markdown canon and protocol documentation.
- `hapa-wiki-viewer`: reader/viewer surface for wiki content.
- `hapa-agent-registry-node`: future agent/tool registry source.
- `hapa-telemetry-node`: local runtime status and telemetry source.

## What Hapa Graphify Adds

- A typed node/edge schema.
- Stable IDs that avoid embedding private paths.
- Truth status labels.
- Record owner and privacy labels.
- Atlas sidecars for large graph exploration.
- Query/path/explain/access parity across CLI, API, UI, MCP, and desktop.
- Public-redacted export and writeback planning.

## What It Does Not Own

Hapa Graphify does not own wiki canon, Second Brain rows, Overwatch board history, Lance indexes, or source repositories. It can generate proposed updates and derived projections, but final authority stays with the owning Hapa node.

## Recommended Ecosystem Workflow

1. Validate sources.
2. Build or refresh compact atlas sidecars from local full runs.
3. Explore the atlas by community/type/source/truth/owner.
4. Drill into bounded records.
5. Generate public-redacted exports or writeback plans.
6. Attach validation evidence to Overwatch when protocol state changes.
