# Hapa Narrative Schema

Generated entries live in `docs/narrative/data/entries.json`.

## Entry Shape

- `id`: stable entry id.
- `kind`: `summary_so_far` or `weekly`.
- `title`: display title.
- `period`: `{start, end, label, timezone}`.
- `tracks.technical.paragraphs`: truthful concise paragraphs.
- `tracks.lore_card.paragraphs`: Hapa lore-card rendition.
- `evidence.counts`: turn/wiki evidence counts.
- `evidence.top_topics`: topic counts from Second Brain turn labels.
- `evidence.top_turn_types`: turn type counts.
- `evidence.top_keywords`: keyword counts from objectives and summaries.
- `evidence.top_turns`: bounded linked turn evidence.
- `evidence.wiki_articles`: linked Second Brain wiki article evidence.
- `evidence.wiki_files`: linked wiki/doc file evidence.
- `evidence.graphify_queries`: query terms, match counts, and top graph matches.
- `evidence.previous_entry_ids`: continuity links.
- `image`: GPT-image prompt, status, fallback SVG path, target PNG path.
- `enrichment`: optional latest enrichment bundle, facts, insights, connections, graph queries, source cards, and pass history.
- `telemetry`: agent id, run id, source counts, query counts, paragraph counts.

## Log Shape

`docs/narrative/data/run-log.ndjson` appends `hapa.narrative.run_event.v1` records with:

- `run_id`
- `started_at`
- `finished_at`
- `duration_ms`
- `entry_count`
- `image_event_count`
- `source_counts`
- `warnings`
- `ok`

`docs/narrative/data/enrichment-log.ndjson` appends `hapa.narrative.enrichment_run.v1` records. The latest enrichment run also lives at `docs/narrative/data/enrichment-run.json`.

## Public Boundary

Generated public files may contain source ids, Hapa URIs, labels, counts, summaries, and redacted graph ids. They must not contain local absolute paths, credentials, raw private media paths, token strings, or full Second Brain row dumps.
