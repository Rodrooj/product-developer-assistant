#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA="$ROOT/standalone-data"

mkdir -p "$DATA/skills" "$DATA/ollama" "$ROOT/standalone-workspace"
chmod 700 "$DATA" "$ROOT/standalone-workspace"

if [[ ! -f "$ROOT/.env.standalone" ]]; then
  cp "$ROOT/.env.standalone.example" "$ROOT/.env.standalone"
  echo "Created .env.standalone. Review FOX_MCP_SOURCE_PATH, model choice, and credentials before starting."
fi
chmod 600 "$ROOT/.env.standalone"

# Keep secrets private, align the upstream Hermes image's optional UID/GID
# remap with the owner of the bind mounts, and create a localhost API key.
python3 - "$ROOT/.env.standalone" <<'PYENV'
from pathlib import Path
import secrets
import sys

path = Path(sys.argv[1])
values = {}
for line in path.read_text().splitlines():
    if "=" in line and not line.lstrip().startswith("#"):
        key, value = line.split("=", 1)
        values[key] = value

defaults = {
    "HERMES_UID": str(__import__("os").getuid()),
    "HERMES_GID": str(__import__("os").getgid()),
    "API_SERVER_KEY": secrets.token_hex(32),
}
for key, value in defaults.items():
    if not values.get(key):
        values[key] = value

lines = path.read_text().splitlines()
seen = set()
out = []
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        key, _ = line.split("=", 1)
        if key in defaults:
            out.append(f"{key}={values[key]}")
            seen.add(key)
            continue
    out.append(line)
for key, value in defaults.items():
    if key not in seen:
        out.append(f"{key}={values[key]}")
path.write_text("\n".join(out) + "\n")
path.chmod(0o600)
PYENV

if [[ ! -f "$DATA/config.yaml" ]]; then
  install -m 0600 "$ROOT/config.standalone.yaml" "$DATA/config.yaml"
fi

if [[ ! -f "$DATA/SOUL.md" ]]; then
  install -m 0600 "$ROOT/SOUL.standalone.md" "$DATA/SOUL.md"
fi

if [[ ! -d "$DATA/skills/productivity" ]]; then
  mkdir -p "$DATA/skills/productivity"
  for skill in "$ROOT"/image/seed/skills/productivity/*; do
    [[ -d "$skill" ]] || continue
    [[ "$(basename "$skill")" == "plow-connectors" ]] && continue
    cp -a "$skill" "$DATA/skills/productivity/"
  done
fi

# Never delete a skill from a persistent profile. A volume copied from the
# Plow deployment needs an explicit backup/manual cleanup before standalone
# startup, otherwise Hermes could load Plow-only tool instructions.
if [[ -d "$DATA/skills/productivity/plow-connectors" ]]; then
  echo "The persistent Hermes profile contains the Plow-only plow-connectors skill." >&2
  echo "Back up standalone-data, then remove that directory manually before starting standalone." >&2
  exit 4
fi

echo "Standalone data initialized at $DATA"
echo "Shared user files belong under $ROOT/standalone-workspace (mounted at /workspace)."
