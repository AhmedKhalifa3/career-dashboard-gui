#!/usr/bin/env bash
# PyInstaller Build Script for Career Cockpit
# Bundles the Python application and all CustomTkinter assets into a standalone binary.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found in .venv."
    exit 1
fi

source .venv/bin/activate

# Install pyinstaller if not present
if ! python -c "import PyInstaller" 2>/dev/null; then
    echo "📦 Installing PyInstaller in .venv..."
    pip install pyinstaller
fi

echo "🔨 Building standalone Career Cockpit executable..."

pyinstaller \
    --noconfirm \
    --name "career-cockpit" \
    --onedir \
    --windowed \
    --collect-all customtkinter \
    --add-data "assets:assets" \
    --hidden-import notion_client \
    --hidden-import yaml \
    --hidden-import requests \
    --hidden-import PIL \
    --hidden-import PIL._tkinter_finder \
    app.py

# Ensure .env is copied to the dist folder so Notion credentials work out of the box
if [ -f ".env" ]; then
    cp .env dist/career-cockpit/.env
fi

echo ""
echo "============================================================"
echo "✨ Build Complete!"
echo "Standalone application bundle created at:"
echo "👉 $SCRIPT_DIR/dist/career-cockpit/career-cockpit"
echo ""
echo "You can launch the binary directly with:"
echo "   $SCRIPT_DIR/dist/career-cockpit/career-cockpit"
echo "============================================================"
