#!/bin/sh
# Install script for gzip (OpenHarmony)
# Usage: sh install.sh [version] [prefix]
#   or:  sh install.sh [prefix]  (installs latest)
set -e

VERSION="${1:-1.13}"
PREFIX="${2:-$HOME/usr/local}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$SCRIPT_DIR/$VERSION/packaging"

if [ ! -d "$PKG_DIR" ]; then
    echo "Error: version $VERSION not found" >&2
    exit 1
fi

cd "$PKG_DIR"
TAR_GZ=$(ls gzip-${VERSION}-ohos-aarch64.tar.gz 2>/dev/null)
if [ -z "$TAR_GZ" ]; then
    echo "Error: package not found for version $VERSION" >&2
    exit 1
fi

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
tar xzf "$TAR_GZ" -C "$TMPDIR"

for d in bin lib include share; do
  [ -d "$TMPDIR/$d" ] && mkdir -p "$PREFIX/$d" && cp -a "$TMPDIR/$d/" "$PREFIX/$d/"
done

chmod +x "$PREFIX/bin/"* 2>/dev/null || true
echo "gzip $VERSION installed to $PREFIX"
