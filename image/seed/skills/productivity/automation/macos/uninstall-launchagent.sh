#!/bin/zsh
set -euo pipefail

LABEL="com.plow.product-assistant.automation-wake"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
WAKE_SCRIPT="$HOME/Library/Application Support/Plow/automation-wake.sh"

if [[ -f "$PLIST" ]]; then
  launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
  rm -f "$PLIST"
fi
rm -f "$WAKE_SCRIPT"

print "Removed $LABEL"
