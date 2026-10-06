#!/usr/bin/env bash
# Installer script for Career Cockpit Linux Desktop Entry
# Integrates Career Cockpit directly into the Ubuntu GNOME Application Launcher & Dock.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$SCRIPT_DIR/run.sh"
ICON="$SCRIPT_DIR/assets/icon.png"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/career-cockpit.desktop"

# Ensure run.sh is executable
chmod +x "$LAUNCHER"

# Ensure assets/icon.png exists
if [ ! -f "$ICON" ]; then
    echo "🎨 Generating app icon..."
    "$SCRIPT_DIR/.venv/bin/python" -c '
from PIL import Image, ImageDraw
import os
size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)
draw.rounded_rectangle([16, 16, 240, 240], radius=48, fill="#1e1e28", outline="#3498db", width=4)
draw.rounded_rectangle([52, 90, 204, 196], radius=20, fill="#2c3e50", outline="#ecf0f1", width=3)
draw.rounded_rectangle([96, 60, 160, 96], radius=14, fill=None, outline="#ecf0f1", width=6)
draw.rectangle([52, 134, 204, 142], fill="#3498db")
draw.rounded_rectangle([114, 126, 142, 150], radius=4, fill="#f39c12", outline="#ffffff", width=2)
os.makedirs("assets", exist_ok=True)
img.save("assets/icon.png")
'
fi

mkdir -p "$DESKTOP_DIR"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Career Cockpit
GenericName=Job Search Dashboard
Comment=Autonomous Job Discovery & Application Tracker
Exec=$LAUNCHER
Icon=$ICON
Path=$SCRIPT_DIR
Terminal=false
Categories=Development;Office;
StartupNotify=true
StartupWMClass=career-cockpit
Keywords=job;scout;notion;career;applications;
EOF

chmod +x "$DESKTOP_FILE"

# Refresh GNOME application database if available
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

# Automatically add to Ubuntu / GNOME Dock Favorites if gsettings is available
if command -v gsettings >/dev/null 2>&1; then
    python3 -c "
import subprocess, ast
try:
    res = subprocess.check_output(['gsettings', 'get', 'org.gnome.shell', 'favorite-apps'], text=True).strip()
    favs = ast.literal_eval(res)
    if 'career-cockpit.desktop' not in favs:
        favs.append('career-cockpit.desktop')
        subprocess.check_call(['gsettings', 'set', 'org.gnome.shell', 'favorite-apps', str(favs)])
        print('⭐ Added Career Cockpit directly to Ubuntu Dock Favorites!')
except Exception:
    pass
" 2>/dev/null || true
fi

echo "============================================================"
echo "🎉 Career Cockpit successfully installed as a Desktop App!"
echo "============================================================"
echo "📍 Desktop Entry: $DESKTOP_FILE"
echo "🖼️ Icon Path:     $ICON"
echo "🚀 Executable:    $LAUNCHER"
echo ""
echo "How to launch:"
echo "1. Press the Super (Windows) key on your keyboard."
echo "2. Type 'Career Cockpit' and press Enter."
echo "3. Right-click the icon in your Ubuntu Dock and select 'Pin to Dash' / 'Add to Favorites'!"
echo "============================================================"
