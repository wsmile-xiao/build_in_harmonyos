#!/bin/sh
# Install script for jq (parameterized)
# Usage: sh install.sh [version] [prefix]
# Example: sh install.sh 1.7.1 $HOME/usr/local
set -e
VER=${1:-1.7.1}
PREFIX=${2:-$HOME/usr/local}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PKG_DIR="$SCRIPT_DIR/$VER/packaging"

if [ ! -f "$PKG_DIR/jq-${VER}-ohos-aarch64.tar.gz" ]; then
  echo "Error: Package not found at $PKG_DIR/jq-${VER}-ohos-aarch64.tar.gz"
  exit 1
fi

TMPDIR=${TMPDIR:-$HOME/tmp}
WORK_DIR=$(mktemp -d "$TMPDIR/jq-install-XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

tar xzf "$PKG_DIR/jq-${VER}-ohos-aarch64.tar.gz" -C "$WORK_DIR"

cd "$WORK_DIR"
for d in bin lib include share; do
  [ -d "$d" ] && mkdir -p "$PREFIX/$d" && cp -a "$d/" "$PREFIX/$d/"
done
chmod +x "$PREFIX/bin/"* 2>/dev/null || true

echo "jq $VER installed to $PREFIX"
if command -v jq >/dev/null 2>&1; then
  jq --version
fi
