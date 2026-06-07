# Security

`hapa-graphify` is local-first and must protect private Hapa memory, generated media, credentials, and unpublished exports.

## Default Blocks

Never ingest these into public graph exports by default:

- `*.db-wal`
- `*.db-shm`
- `.node_token`
- `.env`
- `node_modules/`
- `.git/`
- `tmp/`
- `public/generated/`
- raw private media folders
- generated private source exports

## Runtime Rules

- Bind future services to `127.0.0.1` by default.
- Do not read token files during health/capabilities/source validation.
- Treat `401` and `403` endpoint probes as `auth_required`, not failed health.
- Public exports must redact absolute private paths unless explicitly marked local-only.
- Dry-run is required before ingest, append, export, and writeback.

## Public Export

Use:

```bash
python3 -m hapa_graphify export --source all --public --dry-run --json
```

Public export keeps truth status, source owner, and privacy labels, but redacts absolute local paths to `redacted://local/<hash>`.

See `docs/THREAT_MODEL.md` for threat boundaries and verification.
