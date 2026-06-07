# Hapa Narrative

`hapa-narrative` is a protocol-compliant weekly canon log built from Hapa Second Brain, Hapa wiki/doc files, and Hapa Graphify queries.

It produces two tracks for each entry:

- `technical`: truthful, concise, source-grounded summary.
- `lore_card`: Hapa lore and fantasy trading-card flavor-text rendition of the same evidence.

## Run

```bash
.venv/bin/python -m hapa_graphify narrative run --start-date 2026-01-01 --end-date 2026-06-07 --json
```

Equivalent script:

```bash
.venv/bin/python scripts/run_hapa_narrative.py --start-date 2026-01-01 --end-date 2026-06-07 --json
```

## Images

Each post gets a GPT-image prompt, image queue telemetry, and a deterministic fallback SVG card.

If `OPENAI_API_KEY` is available and image generation is authorized:

```bash
.venv/bin/python scripts/generate_hapa_narrative_images.py --start-date 2026-01-01 --end-date 2026-06-07 --json
```

Without an API key, image jobs stay `queued_openai_api_key_missing` and the app displays fallback SVGs.

## App

Local preview:

```bash
python3 -m http.server 8800 --bind 127.0.0.1 --directory docs
```

Open:

```text
http://127.0.0.1:8800/narrative/
```

GitHub Pages path:

```text
https://calderwong.github.io/hapa-graphify/narrative/
```

## Logs

- `docs/narrative/data/entries.json`: rendered entries.
- `docs/narrative/data/run-log.ndjson`: append-only agent run telemetry.
- `docs/narrative/data/agent-run.json`: latest run summary.
- `docs/narrative/data/image-queue.ndjson`: GPT-image jobs.
- `docs/narrative/images/*.svg`: fallback cards.
- `docs/narrative/images/*.png`: generated image outputs when available.

## Skill

Bundled repeatable skill:

```text
skills/hapa-narrative-weekly/SKILL.md
```

Use it when an agent needs to refresh weekly Hapa canon entries, connect weeks to previous entries, and preserve telemetry.
