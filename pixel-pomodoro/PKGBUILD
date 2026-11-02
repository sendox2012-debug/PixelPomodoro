# Maintainer: you
# Сборка и установка системным пакетом:  makepkg -si
pkgname=pixel-pomodoro
pkgver=1.0.0
pkgrel=1
pkgdesc="Pixel-art pomodoro timer written in tkinter"
arch=('any')
license=('MIT')
depends=('python' 'tk')
optdepends=('libnotify: desktop notifications'
            'pipewire: sound alert (pw-play)'
            'libpulse: sound alert (paplay)')
source=('pixel_pomodoro.py' 'pixel-pomodoro.desktop')
sha256sums=('SKIP' 'SKIP')

build() {
  python "$srcdir/pixel_pomodoro.py" --export-icon "$srcdir/pixel-pomodoro.png"
}

package() {
  install -Dm755 "$srcdir/pixel_pomodoro.py" "$pkgdir/usr/share/$pkgname/pixel_pomodoro.py"
  install -d "$pkgdir/usr/bin"
  printf '#!/bin/sh\nexec python3 /usr/share/%s/pixel_pomodoro.py "$@"\n' "$pkgname" > "$pkgdir/usr/bin/$pkgname"
  chmod 755 "$pkgdir/usr/bin/$pkgname"
  install -Dm644 "$srcdir/pixel-pomodoro.desktop" "$pkgdir/usr/share/applications/$pkgname.desktop"
  install -Dm644 "$srcdir/pixel-pomodoro.png" "$pkgdir/usr/share/icons/hicolor/256x256/apps/$pkgname.png"
}
