#!/bin/sh
# Install script for gdbm (OpenHarmony)
set -e
VERSION="${1:-1.23}"
PREFIX="${2:-$HOME/usr/local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$SCRIPT_DIR/$VERSION/packaging"

if [ ! -d "$PKG_DIR" ]; then
    echo "Error: version $VERSION not found" >&2; exit 1
fi
cd "$PKG_DIR"
TAR_GZ=$(ls gdbm-${VERSION}-ohos-aarch64.tar.gz 2>/dev/null)
if [ -z "$TAR_GZ" ]; then
    echo "Error: package not found" >&2; exit 1
fi
TMPDIR=$(mktemp -d); trap 'rm -rf "$TMPDIR"' EXIT
tar xzf "$TAR_GZ" -C "$TMPDIR"
for d in bin lib include share; do
  [ -d "$TMPDIR/$d" ] && mkdir -p "$PREFIX/$d" && cp -a "$TMPDIR/$d/" "$PREFIX/$d/"
done
chmod +x "$PREFIX/bin/"* 2>/dev/null || true
echo "export LD_LIBRARY_PATH=$PREFIX/lib:\$LD_LIBRARY_PATH"
echo "gdbm $VERSION installed to $PREFIX"
