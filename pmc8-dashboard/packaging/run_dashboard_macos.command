#!/bin/sh
set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
APP_DIR="$SCRIPT_DIR/PMC8_Dashboard_macOS"
LAUNCHER="$APP_DIR/run_dashboard_macos.command"

if [ ! -f "$LAUNCHER" ]; then
    echo "Bundled macOS launcher was not found."
    echo "Expected: $LAUNCHER"
    printf "Press Return to close..."
    read _
    exit 1
fi

chmod +x "$LAUNCHER" 2>/dev/null
exec "$LAUNCHER"
