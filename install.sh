#!/usr/bin/env bash
# Adds To-Do to your app launcher (current user only). Run with --uninstall to remove it.
set -euo pipefail

APP_ID="io.github.berkukcelik.TodoLinux"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
ICONS="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor/scalable/apps"
BIN="$HOME/.local/bin"

if [[ "${1:-}" == "--uninstall" ]]; then
    rm -f "$APPS/$APP_ID.desktop" "$ICONS/$APP_ID.svg" "$BIN/todo-linux"
    echo "Uninstalled. Your tasks are kept in ${XDG_DATA_HOME:-$HOME/.local/share}/todo-linux/"
    exit 0
fi

mkdir -p "$APPS" "$ICONS" "$BIN"
install -m 644 "$DIR/data/todo-linux.svg" "$ICONS/$APP_ID.svg"

cat > "$BIN/todo-linux" <<EOF
#!/usr/bin/env bash
cd "$DIR" && exec python3 -m todo "\$@"
EOF
chmod +x "$BIN/todo-linux"

cat > "$APPS/$APP_ID.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=To-Do
Comment=Keep track of things to do
Exec=$BIN/todo-linux
Icon=$APP_ID
Terminal=false
Categories=Utility;GTK;
Keywords=todo;task;list;
StartupNotify=true
EOF

update-desktop-database "$APPS" 2>/dev/null || true
echo "Installed. Find \"To-Do\" in your app launcher, or run: todo-linux"
