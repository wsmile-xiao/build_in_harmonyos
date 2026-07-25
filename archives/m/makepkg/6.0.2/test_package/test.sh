#!/usr/bin/env bash
set -euo pipefail

: "${MAKEPKG_BIN:?MAKEPKG_BIN is required}"
: "${MAKEPKG_CONF:?MAKEPKG_CONF is required}"

"$MAKEPKG_BIN" --version | grep "makepkg (pacman) 6.0.2"

workdir="makepkg-smoke-$$"
rm -rf "$workdir"
mkdir "$workdir"
trap 'cd .. 2>/dev/null || true; rm -rf "$workdir"' EXIT
cd "$workdir"

cat > PKGBUILD <<'PKGBUILD'
pkgname=conan-makepkg-smoke
pkgver=1.0.0
pkgrel=1
pkgdesc="makepkg Conan smoke package"
arch=('any')
license=('MIT')
source=()
sha256sums=()

package() {
  install -Dm644 /dev/null "$pkgdir/usr/share/conan-makepkg-smoke/marker"
}
PKGBUILD

cp "$MAKEPKG_CONF" makepkg-smoke.conf
printf '%s\n' 'OPTIONS=(!strip docs libtool staticlibs emptydirs zipman purge !debug !lto)' >> makepkg-smoke.conf

PACMAN="${PACMAN:-sh}" "$MAKEPKG_BIN" --config makepkg-smoke.conf --printsrcinfo > .SRCINFO
grep "pkgbase = conan-makepkg-smoke" .SRCINFO
grep "pkgver = 1.0.0" .SRCINFO
