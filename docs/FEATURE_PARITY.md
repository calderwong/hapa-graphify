# Feature Parity

| Capability | API | CLI | UI | Desktop | Data source | Verification | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Health | `/health` | `health` | `/ui` status chip | Electron shell loads `/ui` | local files | `smoke --dry-run` | partial |
| Capabilities | `/capabilities` | `capabilities` | `/ui` latest response | Electron shell loads `/ui` | core feature spine | `capabilities --json` | partial |
| Source registry list | `/api/sources` | `sources list` | `/ui` source select | Electron shell loads `/ui` | `config/hapa-graphify.sources.json` | unit test | partial |
| Source registry validate | `/api/sources` | `sources validate` | `/ui` refresh | Electron shell loads `/ui` | source registry targets | smoke | partial |
| Ingest dry-run | `POST /api/ingest/dry-run` | `ingest --dry-run` | `/ui` Ingest Dry | Electron shell loads `/ui` | source registry targets | smoke | partial |
| Full ingest | Planned | Planned | Planned | Planned | source registry targets | not started | missing |
| Append/update | `/api/append` | `append --since last-success --dry-run` | `/ui` latest response | Electron shell loads `/ui` | run ledger + source signatures | unit test + CLI | partial |
| Reconcile | `/api/reconcile` | `reconcile --against second-brain --dry-run` | Planned | Planned | source signatures | unit test + CLI | partial |
| Report atlas | `/api/reports` | `reports list` | `/ui` report atlas | Electron shell loads `/ui` | compact full-run sidecars | route test + CLI | partial |
| Graph atlas map | `/api/map` | `map` | `/ui` group map + drill | Electron shell loads `/ui` | compact map sidecars | route test + browser | partial |
| Query/browse/path/explain | `/api/query`, `/api/browse`, `/api/path`, `/api/explain` | `query`, `browse`, `path`, `explain`, `mcp call` | `/ui` graph, result list, inspector | Electron shell loads `/ui` | bounded combined graph fragment | unit test + CLI + MCP | partial |
| Hapa ecosystem discovery | `/api/ecosystem/discover` | `ecosystem discover` | `/ui` Discover | Electron shell loads `/ui` | NODE_MAP, Quest Keeper audit, Overwatch configs, local manifests | unit test + CLI | partial |
| Full ecosystem AST analysis | `/api/ecosystem/ast` | `ecosystem ast --full` | `/ui` AST Full | Electron shell loads `/ui` | discovered Hapa codebases + Graphify AST | full report + validation | partial |
| Knowledge/document graph | `/api/knowledge/graph` | `knowledge graph --full` | `/ui` Knowledge Full | Electron shell loads `/ui` | Second Brain, Hapa docs, full wiki, Quest Keeper, Overwatch | full report + validation | partial |
| Export | `/api/export` | `export --dry-run` | `/ui` Export Dry | Electron shell loads `/ui` | graph fragment | unit test + CLI | partial |
| Board writeback | `/api/board/checkpoint` | `board checkpoint --dry-run` | `/ui` Checkpoint Dry | Electron shell loads `/ui` | Overwatch events | unit test + checkpoint | partial |
| Docs viewer | `/ui` | docs files | `/ui` | `bin/hapa-graphify-desktop.sh` | docs | file check | partial |
| Run ledger | `/api/runs` | `ledger record-smoke`, `ledger list` | `/ui` run ledger | Electron shell loads `/ui` | `runs/hapa-graphify-runs.ndjson` | unit test + CLI | partial |
| Conflict/review suggestions | `/api/review-suggestions` | `review-suggestions` | `/ui` Reviews | Electron shell loads `/ui` | graph fragment validation | unit test + CLI | partial |
| Local telemetry probe | `/api/telemetry/probe` | `telemetry probe` | Planned | Planned | loopback HTTP endpoints | unit test + CLI | partial |
| MCP tools | JSONL scaffold | `mcp tools`, `mcp call`, `mcp serve-jsonl` | Planned | Planned | filtered graph context | unit test + CLI | partial |
| Desktop shell | Loopback API | `bin/hapa-graphify-desktop.sh --check` | `/ui` | Electron scaffold | desktop files | desktop smoke check | partial |
| Security/privacy gates | Public export redaction | `export --public --dry-run` | privacy labels visible | Electron shell uses loopback | registry excludes + redaction | unit tests + threat model | partial |
| Fixture/CI corpus | API route fixtures | unittest fixtures | `/ui` route smoke | desktop smoke check | golden fixture | `docs/TESTING.md` | partial |
| Performance baseline | API query route | `benchmark` | UI render limit | desktop loads `/ui` | sampled ecosystem graph | `docs/PERFORMANCE.md` + report | partial |
| Second Brain/Lance writeback | `/api/writeback` | `writeback --dry-run` | latest response inspector | desktop loads `/ui` | public-redacted projection | `docs/WRITEBACK.md` + tests | partial |
