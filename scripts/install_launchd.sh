#!/usr/bin/env bash
# Installs (or reinstalls) the fly LaunchAgents for the current user. Safe to run again.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$HOME/Library/LaunchAgents"
DOMAIN="gui/$(id -u)"
mkdir -p "$DEST" "$REPO/data/logs"

for name in com.fly.run com.fly.digest; do
    sed "s#__REPO__#$REPO#g" "$REPO/launchd/$name.plist" > "$DEST/$name.plist"
    launchctl bootout "$DOMAIN/$name" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$DEST/$name.plist"
    echo "installed $name"
done
