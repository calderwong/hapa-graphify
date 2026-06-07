# Desktop

Status: Electron shell scaffold.

```bash
bin/hapa-graphify-desktop.sh --check
cd desktop && npm install
bin/hapa-graphify-desktop.sh
```

The Electron main process starts:

```bash
python3 -m hapa_graphify serve --host 127.0.0.1 --port 8796
```

Then it opens:

```text
http://127.0.0.1:8796/ui
```

Runtime data stays outside the desktop bundle because the service runs from the repository root and uses the same source registry, run ledger, exports folder, and append-only board event log as the CLI/API.

## Smoke

`bin/hapa-graphify-desktop.sh --check` validates:

- Desktop files exist.
- The main process starts the service.
- The main process loads `/ui`.
- The service working directory is the repository root.

Actual window launch requires Electron dependencies in `desktop/node_modules`.
