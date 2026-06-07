#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ELECTRON_BIN="$ROOT/desktop/node_modules/.bin/electron"

if [[ "${1:-}" == "--check" ]]; then
  node "$ROOT/desktop/smoke-check.mjs"
  exit $?
fi

if [[ ! -x "$ELECTRON_BIN" ]]; then
  echo "Electron is not installed. Run: cd \"$ROOT/desktop\" && npm install"
  echo "API/UI fallback: python3 -m hapa_graphify serve --host 127.0.0.1 --port 8796"
  exit 2
fi

cd "$ROOT"
exec "$ELECTRON_BIN" "$ROOT/desktop/main.js"
