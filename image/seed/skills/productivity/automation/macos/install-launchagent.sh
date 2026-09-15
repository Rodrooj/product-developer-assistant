#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LABEL="com.plow.product-assistant.automation-wake"
AGENTS_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$HOME/Library/Logs"
PLIST="$AGENTS_DIR/$LABEL.plist"
TEMPLATE="$SCRIPT_DIR/$LABEL.plist"
WAKE_SCRIPT="$SCRIPT_DIR/automation-wake.sh"

mkdir -p "$AGENTS_DIR" "$LOG_DIR"
chmod 700 "$WAKE_SCRIPT"

if [[ ! -x "$WAKE_SCRIPT" ]]; then
  print -u2 "automation installer: wake script is not executable"
  exit 1
fi

# Materialize absolute paths so launchd does not depend on shell expansion.
sed \
  -e "s|__AUTOMATION_WAKE_SCRIPT__|$WAKE_SCRIPT|g" \
  -e "s|__HOME__|$HOME|g" \
  "$TEMPLATE" > "$PLIST"

# bootstrap is the modern launchd interface for the per-user GUI domain.
launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
launchctl enable "gui/$(id -u)/$LABEL"

print "Installed $LABEL"
launchctl print "gui/$(id -u)/$LABEL" >/dev/null
print "Verified launchd job: gui/$(id -u)/$LABEL"
