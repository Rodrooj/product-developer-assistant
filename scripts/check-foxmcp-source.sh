#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env.standalone"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing .env.standalone; run scripts/standalone-init.sh first." >&2
  exit 2
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
FOX_DIR="${FOX_MCP_SOURCE_PATH:-../FoxMCP}"
if [[ "$FOX_DIR" != /* ]]; then FOX_DIR="$ROOT/$FOX_DIR"; fi
for f in Cargo.toml Cargo.lock crates/foxmcp-server/src/main.rs crates/foxmcp-server/src/security.rs; do
  [[ -f "$FOX_DIR/$f" ]] || { echo "FoxMCP checkout missing $f: $FOX_DIR" >&2; exit 3; }
done
grep -q 'name = "foxmcp-server"' "$FOX_DIR/crates/foxmcp-server/Cargo.toml"
patch --dry-run --batch -p1 -d "$FOX_DIR" < "$ROOT/integrations/foxmcp/deny-private-browser-targets.patch" >/dev/null
echo "FoxMCP build context and downstream security patch verified: $FOX_DIR"
