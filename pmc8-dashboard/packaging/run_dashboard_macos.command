#!/bin/sh
set -u

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
APP_FILE="$SCRIPT_DIR/PMC8_Dashboard.py"
REQ_FILE="$SCRIPT_DIR/requirements.txt"

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "Python was not found."
    echo "Install Python 3.10 or newer from https://www.python.org/downloads/macos/"
    echo "Then open a new Terminal window and run this launcher again."
    printf "Press Return to close..."
    read _
    exit 1
fi

if [ ! -f "$APP_FILE" ]; then
    echo "PMC8_Dashboard.py was not found beside this launcher."
    echo "Expected: $APP_FILE"
    printf "Press Return to close..."
    read _
    exit 1
fi

echo "Using Python command: $PYTHON_CMD"
"$PYTHON_CMD" -m pip install -r "$REQ_FILE" || {
    echo "Failed to install Python requirements."
    printf "Press Return to close..."
    read _
    exit 1
}

"$PYTHON_CMD" "$APP_FILE"
printf "Press Return to close..."
read _
