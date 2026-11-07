#!/bin/zsh
set -euo pipefail

# Wake/recovery bridge for scheduled Hermes automations.
# It intentionally delegates schedule semantics to Hermes instead of maintaining
# a second job database. launchd can invoke this after login and periodically;
# hermes cron tick decides which jobs are actually due.

LOCK_DIR="${TMPDIR:-/tmp}/plow-product-assistant-automation-wake.lock"
LOG_DIR="${HOME}/.hermes/logs"
mkdir -p "$LOG_DIR"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  exit 0
fi
cleanup() {
  rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# Keep the Mac from entering idle system sleep while this dispatch is active.
# -w ties the assertion to this process; it is not a permanent sleep blocker.
CAFFEINATE_PID=""
if command -v caffeinate >/dev/null 2>&1; then
  caffeinate -i -w $$ >/dev/null 2>&1 &
  CAFFEINATE_PID=$!
fi
cleanup_caffeinate() {
  if [[ -n "$CAFFEINATE_PID" ]]; then
    kill "$CAFFEINATE_PID" 2>/dev/null || true
  fi
}
trap 'cleanup_caffeinate; cleanup' EXIT INT TERM

# Ensure launchd environment can locate hermes and docker
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

HERMES_BIN="${HERMES_BIN:-$(command -v hermes || true)}"
if [[ -z "$HERMES_BIN" ]] && ! command -v docker >/dev/null 2>&1; then
  print -u2 "automation-wake: neither hermes nor docker executable found"
  exit 127
fi

# A single tick is intentionally used: Hermes owns due-job, repeat and
# in-flight semantics. This avoids replaying every missed interval after sleep.
if [[ -n "$HERMES_BIN" ]]; then
  "$HERMES_BIN" cron tick >>"$LOG_DIR/automation-wake.log" 2>&1 || true
fi

# Also tick scheduled jobs inside the agent Docker container if running
if command -v docker >/dev/null 2>&1; then
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "product-developer-assistant-agent-1"; then
    docker exec product-developer-assistant-agent-1 /command/s6-envdir /run/s6/container_environment sh -c "export HOME=/var/lib/hermes; su -s /bin/sh hermes -c 'hermes cron tick'" >>"$LOG_DIR/automation-wake.log" 2>&1 || true
  fi
fi
