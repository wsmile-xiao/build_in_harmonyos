#!/bin/sh
# Install script for wget — parameterized version
set -e
VERSION="${1:-1.19.1}"
PREFIX="${2:-$HOME/usr/local}"
ARCHIVE_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Installing wget $VERSION to $PREFIX..."

# Extract tarball
TAR="$ARCHIVE_DIR/$VERSION/packaging/wget-$VERSION-ohos-aarch64.tar.gz"
if [ ! -f "$TAR" ]; then
    echo "Error: $TAR not found"
    exit 1
fi

TMPDIR="${TMPDIR:-$HOME/tmp}"
TMP=$(mktemp -d "$TMPDIR/wget-install.XXXXXX")
tar xzf "$TAR" -C "$TMP"

# Copy files
for d in bin lib include share doc; do
    [ -d "$TMP/$d" ] && cp -a "$TMP/$d/" "$PREFIX/$d/" 2>/dev/null || true
done

rm -rf "$TMP"
chmod +x "$PREFIX/bin/wget" 2>/dev/null || true

echo "wget $VERSION installed to $PREFIX"
echo "Run: wget --version"
