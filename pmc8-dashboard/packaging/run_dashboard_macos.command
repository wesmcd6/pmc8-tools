#!/bin/sh
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/PMC8_Dashboard_macOS"
cd "$APP_DIR" || exit 1
python3 -m pip install -r requirements.txt
python3 PMC8_Dashboard.py
