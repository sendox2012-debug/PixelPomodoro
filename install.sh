#!/bin/sh
# Установка Pixel Pomodoro для текущего пользователя (без root).
#   ./install.sh              установить в ~/.local
#   ./install.sh --uninstall  удалить
set -e

PREFIX="${PREFIX:-$HOME/.local}"
HERE="$(cd "$(dirname "$0")" && pwd)"
APPDIR="$PREFIX/share/pixel-pomodoro"
BIN="$PREFIX/bin/pixel-pomodoro"
DESKTOP="$PREFIX/share/applications/pixel-pomodoro.desktop"
ICON="$PREFIX/share/icons/hicolor/256x256/apps/pixel-pomodoro.png"

if [ "$1" = "--uninstall" ]; then
    rm -rf "$APPDIR" "$BIN" "$DESKTOP" "$ICON"
    command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
    echo "Pixel Pomodoro удалён. Настройки остались в ~/.config/pixel-pomodoro"
    exit 0
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
    echo "Не найден tkinter. На Arch установи его так:  sudo pacman -S tk" >&2
    exit 1
fi

mkdir -p "$APPDIR" "$PREFIX/bin" "$PREFIX/share/applications" "$(dirname "$ICON")"

install -m 755 "$HERE/pixel_pomodoro.py" "$APPDIR/pixel_pomodoro.py"
python3 "$APPDIR/pixel_pomodoro.py" --export-icon "$ICON"

cat > "$BIN" <<EOF
#!/bin/sh
exec python3 "$APPDIR/pixel_pomodoro.py" "\$@"
EOF
chmod 755 "$BIN"

sed "s|^Exec=.*|Exec=$BIN|" "$HERE/pixel-pomodoro.desktop" > "$DESKTOP"
chmod 644 "$DESKTOP"

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$PREFIX/share/applications" 2>/dev/null || true
command -v gtk-update-icon-cache >/dev/null 2>&1 && gtk-update-icon-cache -q -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true

echo "Готово! Ищи «Pixel Pomodoro» в меню приложений или запусти: pixel-pomodoro"
case ":$PATH:" in
    *":$PREFIX/bin:"*) ;;
    *) echo "Подсказка: добавь $PREFIX/bin в PATH, чтобы запускать из терминала." ;;
esac
