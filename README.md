# Pixel Pomodoro

Пиксельный помодоро-таймер на чистом tkinter. Фиолетово-розовая тема, маскот-помидорка,
8-битный звук, уведомления рабочего стола.

## Установка на Arch

```bash
sudo pacman -S python tk            # зависимости
sudo pacman -S libnotify            # по желанию: уведомления
./install.sh                        # установка в ~/.local (без root)
```

После этого ищи **Pixel Pomodoro** в меню приложений или запусти `pixel-pomodoro`.
Удалить: `./install.sh --uninstall`.

Системным пакетом (pacman будет знать о нём): `makepkg -si`.

