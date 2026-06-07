---
name: hapa-narrative-weekly
description: Generate Hapa canon narrative blog entries from Hapa Second Brain, wiki, and Hapa Graphify evidence. Use when asked to summarize what happened in Hapa by week, create truthful plus lore-stylized narrative tracks, connect entries to previous Hapa content, or refresh the hapa-narrative app and logs.
---

# Hapa Narrative Weekly

## Workflow

1. Run source checks:

```bash
.venv/bin/python -m hapa_graphify health --deep --json
.venv/bin/python -m hapa_graphify sources validate --json
```

2. Generate or refresh entries:

```bash
.venv/bin/python scripts/run_hapa_narrative.py --start-date 2026-01-01 --end-date 2026-06-07 --json
```

3. Generate local PNG illustrations and, if `OPENAI_API_KEY` is available and image generation is authorized, replace them with GPT-image outputs:

```bash
.venv/bin/python scripts/generate_hapa_narrative_images.py --start-date 2026-01-01 --end-date 2026-06-07 --json
```

Without `OPENAI_API_KEY`, the run still writes deterministic local PNG illustrations, GPT-image prompts, fallback SVG cards, and queued image telemetry.

4. Review the static app:

```bash
python3 -m http.server 8800 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8800/narrative/`.

## Required Outputs

- `docs/narrative/data/entries.json`: current blog entries.
- `docs/narrative/data/run-log.ndjson`: append-only agent run telemetry.
- `docs/narrative/data/agent-run.json`: latest run summary.
- `docs/narrative/data/image-queue.ndjson`: local illustration and GPT-image queue status records.
- `docs/narrative/images/*.svg`: deterministic fallback visual cards.
- `docs/narrative/images/*.png`: deterministic local illustrations, or GPT-image replacements when available.

## Evidence Rules

- Prefer event time from `ai_chat_turns.turn_started_at`.
- Use `wiki_articles.updated_at` or changed wiki/doc file mtimes for wiki evidence.
- Run Hapa Graphify queries for top weekly topics/keywords and include match telemetry.
- Link source evidence with `hapa://second-brain/...` and `hapa://wiki/...` URIs.
- Preserve empty weeks instead of inventing activity.
- Keep private local paths out of public output.

## Tracks

- `technical`: concise, source-grounded, explicitly scoped to observed data.
- `lore_card`: Hapa lore and fantasy trading-card flavor-text rendition. Do not alter counts, dates, or source claims.

## Reference

Read `references/schema.md` when changing the entry schema, app reader, or log format.
