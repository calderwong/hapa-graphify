# Hapa Narrative

`hapa-narrative` is a protocol-compliant weekly canon log built from Hapa Second Brain, Hapa wiki/doc files, and Hapa Graphify queries.

It produces two tracks for each entry:

- `technical`: truthful, concise, source-grounded summary.
- `lore_card`: Hapa lore and fantasy trading-card flavor-text rendition of the same evidence.

## Run

Refresh Hapa Turns before generating weekly canon, especially after new ChatGPT, Grok, Codex, Hermes, Gemini/NotebookLM, Windsurf, or Antigravity exports/sessions are available:

```bash
cd "$HAPA_SECOND_BRAIN_ROOT"
python3 hapa_second_brain/second_brain.py import-ai-chats
python3 hapa_second_brain/second_brain.py turn-profile --limit 20
python3 hapa_second_brain/second_brain.py turn-sources --limit 40
```

`import-ai-chats` is idempotent. It refreshes the Second Brain `ai_chat_*` tables that `hapa-narrative` reads for weekly turn counts, top turns, topic extraction, and source links.

```bash
.venv/bin/python -m hapa_graphify narrative run --start-date 2026-01-01 --end-date 2026-06-07 --json
```

Equivalent script:

```bash
.venv/bin/python scripts/run_hapa_narrative.py --start-date 2026-01-01 --end-date 2026-06-07 --json
```

## Enrichment

Run the enrichment pass after the base narrative exists:

```bash
.venv/bin/python scripts/run_hapa_narrative_enrichment.py --json
```

Equivalent CLI:

```bash
.venv/bin/python -m hapa_graphify narrative enrich --json
```

The pass reads the weekly entries, selects expansion terms from each entry plus adjacent/overall canon context, queries Hapa Graphify, gathers bounded source cards from configured stores, and writes facts, technical insights, lore-card insights, and connections back into each entry. It tracks the agent and pass history in `entry.enrichment.passes`.

The weekly Codex automation named `Hapa Narrative Enrichment Weekly` (`hapa-narrative-enrichment-weekly`) runs turn mining first, regenerates the base narrative through the current date, refreshes images, then reruns this enrichment pass on Monday mornings local time.

## Images

Each post gets a deterministic local illustrated PNG, a fallback SVG card, a GPT-image prompt, and image queue telemetry.

Install the optional image renderer before a full local refresh:

```bash
.venv/bin/python -m pip install -e ".[images]"
```

If `OPENAI_API_KEY` is available and image generation is authorized:

```bash
.venv/bin/python scripts/generate_hapa_narrative_images.py --start-date 2026-01-01 --end-date 2026-06-07 --json
```

Without an API key, the app displays the local illustrated PNGs, keeps the deterministic SVGs as fallbacks, and records GPT-image jobs as `queued_openai_api_key_missing`.

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
- `docs/narrative/data/enrichment-run.json`: latest enrichment pass summary.
- `docs/narrative/data/enrichment-log.ndjson`: append-only enrichment pass telemetry.
- `docs/narrative/data/image-queue.ndjson`: local illustration and GPT-image queue status records.
- `docs/narrative/images/*.png`: local illustrated PNGs, or GPT-image replacements when generated.
- `docs/narrative/images/*.svg`: deterministic fallback cards.

## Skill

Bundled repeatable skill:

```text
skills/hapa-narrative-weekly/SKILL.md
skills/hapa-narrative-enrichment/SKILL.md
```

Use these when an agent needs to refresh weekly Hapa canon entries, enrich them with additional facts and connections, and preserve telemetry.

## Weekly Order

1. Use `$hapa-turn-miner` to refresh all AI conversation sources into Second Brain.
2. Run `hapa-narrative-weekly` from `2026-01-01` through the current date so newly mined turns can affect the latest week.
3. Regenerate local/GPT-image narrative illustrations for the same date window.
4. Run `hapa-narrative-enrichment` so added facts, lore insights, and connections are based on the refreshed turn store.
5. Run tests/privacy checks before publishing public Pages output.
