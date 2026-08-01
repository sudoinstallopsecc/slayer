#!/usr/bin/env bash
set -euo pipefail

echo "Installing SLAYER dependencies..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but was not found in PATH." >&2
    exit 1
fi

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

chmod +x slayer.py

echo "Done. Run the tool with: python3 slayer.py"
