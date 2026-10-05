#!/usr/bin/env bash
# Quick launcher for Career Cockpit GUI
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

source .venv/bin/activate
exec python app.py "$@"
