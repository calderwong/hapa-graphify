# Data Boundary

`hapa-graphify` reads Hapa ecosystem sources and produces graph projections. It must not turn local private records into public artifacts by accident.

## Local Private By Default

These sources are local-private unless a future export explicitly redacts them:

- Second Brain SQLite database.
- Hapa Worldbuilding Wiki operations and raw/source folders.
- Overwatch Kanban event logs.
- Quest Keeper audit artifacts.
- Local node paths.
- Generated graph outputs and run ledgers.

## Public Reference

These may be used as public reference:

- Upstream Graphify repository metadata and source files from the reviewed commit.
- Hapa docs only when already designated public-safe by the owning node.

## Excluded By Default

- SQLite WAL/SHM files.
- Credentials and token files.
- Raw private media.
- Generated private source exports.
- `node_modules`, `.git`, `tmp`, `public/generated`.

## Write Rule

All ingestion starts as dry-run. Write modes may create only `hapa-graphify` run artifacts and graph outputs unless the user explicitly authorizes writeback to another Hapa node.
