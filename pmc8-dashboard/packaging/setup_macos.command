#!/bin/sh
set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
APP_DIR="$SCRIPT_DIR"

# Support being run either from inside PMC8_Dashboard_macOS or from dist_bundle.
if [ -d "$SCRIPT_DIR/PMC8_Dashboard_macOS" ]; then
    APP_DIR="$SCRIPT_DIR/PMC8_Dashboard_macOS"
fi

LAUNCHER="$APP_DIR/run_dashboard_macos.command"
FRIENDLY_LAUNCHER="$APP_DIR/run_PMC8-Dashboard.command"
REQ_FILE="$APP_DIR/requirements.txt"
P1LOAD="$APP_DIR/p1load_package (1)/p1load"
P1LOAD_SCRIPT="$APP_DIR/p1load_package (1)/run_p1load.sh"

printf '\nPMC8 Dashboard macOS setup\n'
printf 'App folder: %s\n\n' "$APP_DIR"

if command -v xattr >/dev/null 2>&1; then
    echo "Clearing Gatekeeper quarantine attributes..."
    xattr -dr com.apple.quarantine "$APP_DIR" 2>/dev/null || true
fi

if [ -f "$LAUNCHER" ]; then
    chmod +x "$LAUNCHER" 2>/dev/null || true
else
    echo "WARNING: launcher not found: $LAUNCHER"
fi

if [ -f "$FRIENDLY_LAUNCHER" ]; then
    chmod +x "$FRIENDLY_LAUNCHER" 2>/dev/null || true
fi

if [ -f "$P1LOAD" ]; then
    chmod +x "$P1LOAD" 2>/dev/null || true
else
    echo "WARNING: p1load helper not found: $P1LOAD"
fi

if [ -f "$P1LOAD_SCRIPT" ]; then
    chmod +x "$P1LOAD_SCRIPT" 2>/dev/null || true
fi

REQUIRED_PY_FILES="PMC8_Dashboard.py upload_dialog.py p1_loader.py network_management.py"
for file in $REQUIRED_PY_FILES; do
    if [ ! -f "$APP_DIR/$file" ]; then
        if [ -f "$SCRIPT_DIR/$file" ]; then
            echo "Installing missing $file from setup folder..."
            cp "$SCRIPT_DIR/$file" "$APP_DIR/$file" || true
        elif [ -f "$SCRIPT_DIR/../$file" ]; then
            echo "Installing missing $file from parent folder..."
            cp "$SCRIPT_DIR/../$file" "$APP_DIR/$file" || true
        fi
    fi

    if [ ! -f "$APP_DIR/$file" ]; then
        echo "Missing required application file: $APP_DIR/$file"
        echo "Restore the complete PMC8 Dashboard folder or re-extract the ZIP."
        printf "Press Return to close..."
        read _
        exit 1
    fi
done

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo ""
    echo "Python was not found. Install Python 3.10 or newer from:"
    echo "https://www.python.org/downloads/macos/"
    echo "Then run this setup script again."
    printf "Press Return to close..."
    read _
    exit 1
fi

echo "Using Python command: $PYTHON_CMD"
if [ -f "$REQ_FILE" ]; then
    "$PYTHON_CMD" -m pip install -r "$REQ_FILE" || {
        echo ""
        echo "Failed to install Python requirements."
        printf "Press Return to close..."
        read _
        exit 1
    }
else
    echo "WARNING: requirements.txt not found: $REQ_FILE"
fi

echo ""
echo "Setup complete. Launching PMC8 Dashboard..."
echo ""
echo "If macOS still blocks p1load during first firmware upload, open System Settings > Privacy & Security and choose Allow Anyway for p1load."
echo ""

if [ -f "$FRIENDLY_LAUNCHER" ]; then
    cd "$APP_DIR" || exit 1
    exec "$FRIENDLY_LAUNCHER"
fi

if [ -f "$LAUNCHER" ]; then
    cd "$APP_DIR" || exit 1
    exec "$LAUNCHER"
fi

echo "Launcher was not found: $LAUNCHER"
printf "Press Return to close..."
read _
exit 1
