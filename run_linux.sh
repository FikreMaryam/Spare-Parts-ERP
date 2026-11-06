#!/usr/bin/env bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "==============================================="
echo "   Starting Spare Parts ERP System (Linux)     "
echo "==============================================="

"$SCRIPT_DIR/venv_linux/bin/python3" "$SCRIPT_DIR/launcher.py"
