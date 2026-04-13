#!/bin/sh
set -e
VERSION="${1:-3.3.0}"
PREFIX="${2:-$HOME/usr/local}"
ARCHIVE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing rsync $VERSION to $PREFIX..."
TAR="$ARCHIVE_DIR/$VERSION/packaging/rsync-$VERSION-ohos-aarch64.tar.gz"
if [ ! -f "$TAR" ]; then echo "Error: $TAR not found"; exit 1; fi

TMPDIR="${TMPDIR:-$HOME/tmp}"
TMP=$(mktemp -d "$TMPDIR/rsync-install.XXXXXX")
tar xzf "$TAR" -C "$TMP"
for d in bin lib include share doc; do
    [ -d "$TMP/$d" ] && cp -a "$TMP/$d/" "$PREFIX/$d/" 2>/dev/null || true
done
rm -rf "$TMP"
chmod +x "$PREFIX/bin/rsync" "$PREFIX/bin/rsync-ssl" 2>/dev/null || true
echo "rsync $VERSION installed to $PREFIX"
echo "Run: rsync --version"
