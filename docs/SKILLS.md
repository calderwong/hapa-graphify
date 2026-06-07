# Hapa Skills Map

This repo exposes CLI/API/UI/MCP/Desktop access points, but agents should also use the broader Hapa skill ecosystem when a task crosses into board operations, wiki protocols, lineage, media, or design systems.

## Core Skills For Hapa Graphify Work

| Skill | Use When | Relationship To Hapa Graphify |
| --- | --- | --- |
| `hapa-board-keeper` | Refreshing, auditing, or filling Hapa Quest Keeper and Overwatch Kanban board states. | Board evidence, protocol checkpoints, task state, and review cards. |
| `hapa-flow-explainer` | Creating or updating multi-node flow explainers, process-flow cards, Node Space scenarios, or protocol walkthroughs. | Turns graph clusters into human-readable process docs and wiki cards. |
| `hapa-turn-miner` | Mining ChatGPT, NotebookLM, Gemini, or future AI exports into Second Brain turn cards. | Produces or refreshes conversation nodes that Hapa Graphify can ingest. |
| `hapa-turn-result-lineage` | Tracing AI conversation turns into learned sources, applied skills, artifacts, and outcomes. | Adds lineage edges between turns, skills, docs, media, and node work. |
| `hapa-astros-design` | Updating Hapa operator dashboards, wiki viewers, node dashboards, and graph UIs. | Keeps the UI consistent with the Hapa/Astros operator aesthetic. |
| `hapa-narrative-weekly` | Refreshing the Hapa weekly canon narrative entries. | Uses Second Brain, wiki, and Graphify query evidence to produce the public narrative log. |
| `hapa-narrative-enrichment` | Adding more facts, lore insights, and connections to existing weekly narrative entries. | Runs the additive enrichment pass and tracks pass/agent telemetry. |

## Adjacent Skills

| Skill | Use When | Relationship To Hapa Graphify |
| --- | --- | --- |
| `hapa-marlin-artifact-flow` | Processing large local video artifact folders through `.hapaMarlin`. | Artifact folders can become graph nodes, but raw media stays local-private. |
| `hapa-video-flow-dancer` | Building local-first avatar video flow trees. | Video flow trees can be represented as derived graph projections. |
| `hapa-avatar-3d-pipeline` | Converting avatar sheets or photos into Trellis-ready 3D assets. | Avatar asset lineage belongs in graph metadata, not public exports. |

## Agent Routing

Use Hapa Graphify directly when the task is graph discovery, map exploration, query/path/explain, source registry validation, report generation, public demo generation, or writeback planning.

Use a Hapa skill first when the task asks to modify or interpret a source-of-truth system:

- Board or project state: `hapa-board-keeper`.
- Wiki/protocol explanation: `hapa-flow-explainer`.
- Conversation ingestion: `hapa-turn-miner`.
- Result lineage: `hapa-turn-result-lineage`.
- Hapa UI visual design: `hapa-astros-design`.
- Weekly canon enrichment: `hapa-narrative-enrichment`.

After the skill completes, run Hapa Graphify again to refresh the relevant map, query, or report sidecar.

## Access Pattern

1. Validate sources with Hapa Graphify.
2. Use the specific Hapa skill to alter or interpret the owning system.
3. Run the narrow graph command for feedback.
4. Run a full graph command only when coverage evidence is required.
5. Attach dry-run output or validation evidence to Overwatch when protocol state changes.

## Safety

Skills can expose sensitive local context. Preserve the same boundary as Hapa Graphify:

- Raw folders, private media, DBs, token files, and local paths stay out of public exports.
- Write-capable actions stay dry-run until a human or protocol grants authority.
- Truth labels should distinguish source facts from inferred relationships.
