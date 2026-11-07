#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT/.env.standalone"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "Run scripts/standalone-init.sh and configure .env.standalone first." >&2
  exit 2
fi
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a
MODEL="${LOCAL_MODEL:-qwen3:4b}"
mkdir -p "$ROOT/standalone-data/ollama"
AVAILABLE_KB="$(df -Pk "$ROOT/standalone-data/ollama" | awk 'NR==2 {print $4}')"
MIN_FREE_KB="$((6 * 1024 * 1024))"
if [[ "$AVAILABLE_KB" -lt "$MIN_FREE_KB" ]]; then
  echo "Not enough free disk space to pull $MODEL safely." >&2
  echo "Available: $((AVAILABLE_KB / 1024 / 1024)) GiB; recommended minimum: 6 GiB." >&2
  echo "Free/expand disk space or use an Ollama endpoint on another machine." >&2
  exit 3
fi
cd "$ROOT"
docker compose --env-file .env.standalone -f compose.standalone.yml exec -T ollama ollama pull "$MODEL"
