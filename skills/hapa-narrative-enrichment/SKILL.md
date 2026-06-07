---
name: hapa-narrative-enrichment
description: Enrich existing Hapa Narrative weekly canon entries with additional bounded facts, lore-aware insights, Graphify connections, source cards, pass telemetry, and agent run logs. Use when asked to run or refresh a Hapa narrative enrichment pass, add more context to weekly entries, connect weeks to adjacent canon, track enrichment agents, or operate the weekly enrichment trigger.
---

# Hapa Narrative Enrichment

Use this skill after the base `hapa-narrative-weekly` run exists. The enrichment pass is additive: it reads `docs/narrative/data/entries.json`, selects context terms per entry, queries Hapa Graphify and local Hapa stores, writes public-safe enrichment bundles back into entries, and appends pass telemetry.

## Workflow

1. If this is a weekly or canonical refresh, run `$hapa-turn-miner` first and regenerate the base narrative before enriching. Enrichment is additive to `entries.json`, so it should see the freshest weekly evidence:

```bash
cd "$HAPA_SECOND_BRAIN_ROOT"
python3 hapa_second_brain/second_brain.py import-ai-chats
python3 hapa_second_brain/second_brain.py turn-profile --limit 20
```

Then return to this repo and run:

```bash
.venv/bin/python scripts/run_hapa_narrative.py --start-date 2026-01-01 --end-date <current-date> --json
.venv/bin/python scripts/generate_hapa_narrative_images.py --start-date 2026-01-01 --end-date <current-date> --json
```

2. Confirm the base narrative exists:

```bash
test -f docs/narrative/data/entries.json
```

3. Run the enrichment pass:

```bash
.venv/bin/python scripts/run_hapa_narrative_enrichment.py --json
```

Equivalent CLI:

```bash
.venv/bin/python -m hapa_graphify narrative enrich --json
```

4. Review the latest run:

```bash
cat docs/narrative/data/enrichment-run.json
tail -1 docs/narrative/data/enrichment-log.ndjson
```

5. Preview the static app:

```bash
python3 -m http.server 8800 --bind 127.0.0.1 --directory docs
```

Open `http://127.0.0.1:8800/narrative/`.

## Outputs

- `docs/narrative/data/entries.json`: entries with `enrichment` bundles.
- `docs/narrative/data/enrichment-run.json`: latest enrichment run summary.
- `docs/narrative/data/enrichment-log.ndjson`: append-only enrichment pass log.
- `docs/narrative/index.html`: renders enrichment facts, insights, and connections.

## Rules

- Preserve the base technical and lore paragraphs unless explicitly asked to rewrite them.
- For recurring weekly runs, never enrich against a stale turn store; run turn mining and base narrative refresh first.
- Keep enrichment public-safe: source IDs, Hapa URIs, labels, counts, summaries, and redacted graph IDs are allowed; local absolute paths, credentials, raw private media paths, and full database rows are not.
- Treat facts as bounded observations from configured stores. Label inferred continuity as `derived_or_inferred`.
- Preserve pass history in `entry.enrichment.passes`; do not overwrite the append-only log.
- If the base narrative was regenerated, run enrichment again afterward because `entries.json` is rewritten by the base generator.

Read `references/schema.md` before changing the entry schema, log format, app renderer, or automation prompt.
