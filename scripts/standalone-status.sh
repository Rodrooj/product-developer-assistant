#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
docker compose --env-file .env.standalone -f compose.standalone.yml ps
docker compose --env-file .env.standalone -f compose.standalone.yml exec -T ollama ollama list
docker compose --env-file .env.standalone -f compose.standalone.yml exec -T agent hermes mcp list
