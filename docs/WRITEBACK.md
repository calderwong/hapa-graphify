# Writeback

Status: dry-run planner.

```bash
python3 -m hapa_graphify writeback --target all --dry-run --output reports/writeback-plan.json --json
```

## Second Brain Rows

The planner emits proposed rows for:

- `wiki_articles`: generated graph summary.
- `ecosystem_connections`: Hapa Graphify to Second Brain projection relationship.

Every proposed row includes:

- `run_id`
- `truth_status`
- `record_owner`
- `operation`
- target table

No SQLite mutation occurs in dry-run mode.

## Lance JSONL Shape

Each Lance-ready row has:

```json
{
  "id": "run-id:graph-summary",
  "text": "Hapa Graphify public projection summary.",
  "metadata": {
    "run_id": "run-id",
    "source": "hapa-graphify",
    "record_owner": "hapa-graphify",
    "truth_status": "derived_or_inferred",
    "privacy": "public-redacted",
    "format": "lance-jsonl-ready"
  }
}
```

## Authority

Non-dry-run writeback requires a separate authorized writer. Hapa Graphify only creates the plan and public-redacted projection by default.
