#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$ROOT/scripts/standalone-init.sh"
"$ROOT/scripts/check-foxmcp-source.sh"

# Rust + Chromium layers and the Hermes image need more temporary disk than
# the final compressed image. Refuse before Docker starts a build on a nearly
# full host.
AVAILABLE_KB="$(df -Pk "$ROOT" | awk 'NR==2 {print $4}')"
MIN_FREE_KB="$((10 * 1024 * 1024))"
if [[ "$AVAILABLE_KB" -lt "$MIN_FREE_KB" ]]; then
  echo "Not enough free disk space to build the standalone agent safely." >&2
  echo "Available: $((AVAILABLE_KB / 1024 / 1024)) GiB; recommended minimum: 10 GiB." >&2
  echo "Free/expand disk space or build the image on another Linux host." >&2
  exit 3
fi

cd "$ROOT"
docker compose --env-file .env.standalone -f compose.standalone.yml up -d --build
