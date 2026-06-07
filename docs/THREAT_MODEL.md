# Threat Model

## Assets

- Hapa Second Brain SQLite data and derived graph fragments.
- Local Hapa node paths, board evidence paths, wiki operations docs, and run ledgers.
- Credentials, token files, private exports, raw generated media, WAL/SHM sidecars, and unpublished source material.

## Trust Boundaries

- CLI/API/UI/MCP/desktop are local-first and bind to `127.0.0.1` by default.
- Source registry targets are read-only unless an explicit append/write protocol grants authority.
- Public graph export is a separate mode from local graph export.

## Default Controls

- Credential-like paths are skipped during file iteration: `.env`, `.node_token`, WAL/SHM files, `tmp/`, `.git/`, `node_modules/`, `public/generated/`, `Raw/`, and `Private/`.
- Loopback telemetry never reads token files and sends no authorization headers.
- Public export redacts private absolute paths to `redacted://local/<hash>`.
- Privacy labels remain visible after redaction.
- Full ingest and writeback are dry-run/authority-gated.
- MCP tools enforce a graph size guard and query-first workflow.

## Failure Modes

- If a source exceeds graph guard limits, the tool returns `graph_too_large`.
- If a local endpoint needs auth, telemetry records `auth_required` rather than fetching secrets.
- If a source disappears, append dry-run emits tombstone candidates instead of deleting graph facts silently.

## Verification

```bash
python3 -m unittest discover -s tests
python3 -m hapa_graphify export --source hapa-front-door-docs --public --dry-run --json
python3 -m hapa_graphify telemetry probe --url http://127.0.0.1:9/health --json
```
