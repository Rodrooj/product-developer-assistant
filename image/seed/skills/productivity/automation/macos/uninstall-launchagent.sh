#!/bin/zsh
set -euo pipefail

LABEL="com.plow.product-assistant.automation-wake"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ -f "$PLIST" ]]; then
  launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
  rm -f "$PLIST"
fi

print "Removed $LABEL"
