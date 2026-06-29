#!/bin/sh
set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
APP_DIR="$SCRIPT_DIR"

# Support being run either from inside PMC8_Dashboard_macOS or from dist_bundle.
if [ -d "$SCRIPT_DIR/PMC8_Dashboard_macOS" ]; then
    APP_DIR="$SCRIPT_DIR/PMC8_Dashboard_macOS"
fi

LAUNCHER="$APP_DIR/run_dashboard_macos.command"

if [ ! -f "$LAUNCHER" ]; then
    echo "PMC8 Dashboard launcher was not found."
    echo "Expected: $LAUNCHER"
    echo "Restore the complete PMC8 Dashboard folder or re-extract the ZIP."
    printf "Press Return to close..."
    read _
    exit 1
fi

chmod +x "$LAUNCHER" 2>/dev/null || true
cd "$APP_DIR" || exit 1
exec "$LAUNCHER"
