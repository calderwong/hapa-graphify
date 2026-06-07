# Hapa Narrative Enrichment Schema

## Entry Enrichment

Each enriched entry has `entry.enrichment`:

- `schema`: `hapa.narrative.entry_enrichment.v1`.
- `latest_pass_id`: pass/run id that last updated the bundle.
- `updated_at`: UTC timestamp.
- `summary`: public-safe concise enrichment summary.
- `selection`: why the entry terms were selected and the terms queried.
- `facts`: bounded facts with labels, detail, optional links, and truth status.
- `insights`: `technical` and `lore_card` insight strings.
- `connections`: adjacent entry, recurring topic, and Graphify node links.
- `graphify_queries`: query terms, match counts, and top matches.
- `source_cards`: bounded Second Brain/wiki/wiki-file context cards.
- `passes`: pass history records with `pass_id`, `run_id`, `agent_id`, counts, and timestamps.

## Logs

`docs/narrative/data/enrichment-log.ndjson` appends `hapa.narrative.enrichment_run.v1` records:

- `pass_id`
- `run_id`
- `agent_id`
- `started_at`
- `finished_at`
- `duration_ms`
- `entries_seen`
- `entries_enriched`
- `graphify_query_count`
- `source_counts`
- `output`
- `pass_log`
- `warnings`
- `ok`

`docs/narrative/data/enrichment-run.json` mirrors the latest run event.

## Automation

The weekly trigger should run the same sequence as humans:

```bash
cd "$HAPA_SECOND_BRAIN_ROOT"
python3 hapa_second_brain/second_brain.py import-ai-chats
python3 hapa_second_brain/second_brain.py turn-profile --limit 20
cd "$HAPA_GRAPHIFY_ROOT"
.venv/bin/python scripts/run_hapa_narrative.py --start-date 2026-01-01 --end-date <current-date> --json
.venv/bin/python scripts/generate_hapa_narrative_images.py --start-date 2026-01-01 --end-date <current-date> --json
.venv/bin/python scripts/run_hapa_narrative_enrichment.py --json
```

The automation should then run tests/privacy checks, commit public-safe generated changes, push, and report turn-mining counts, base narrative run id, image queue summary, enrichment pass id, entry count, warnings, and Pages status.
