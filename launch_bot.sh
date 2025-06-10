#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ -d "lysara-env" ]; then
    echo "Activating virtual environment..."
    source "lysara-env/bin/activate"
else
    echo "Virtual environment 'lysara-env' not found" >&2
fi

echo "Launching Lysara Investments bot..."
python launcher.py "$@"
