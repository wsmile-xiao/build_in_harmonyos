#!/bin/sh
# Install script for tar 1.35
set -e
PREFIX=${1:-$HOME/usr/local}
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
for d in bin lib include share; do
  [ -d "$d" ] && cp -a "$d/" "$PREFIX/$d/"
done
chmod +x "$PREFIX/bin/"* 2>/dev/null || true
echo 'tar 1.35 installed to $PREFIX'
