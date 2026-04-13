#!/bin/sh
# Install script for file 5.45
set -e
PREFIX=${1:-$HOME/usr/local}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
for d in bin lib include share; do
  [ -d "$d" ] && cp -a "$d/" "$PREFIX/$d/"
done
chmod +x "$PREFIX/bin/"* 2>/dev/null || true
echo 'file 5.45 installed to $PREFIX'
