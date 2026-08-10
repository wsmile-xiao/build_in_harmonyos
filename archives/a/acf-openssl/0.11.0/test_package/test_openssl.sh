#!/bin/bash
# Verify the packaged ACF openssl module assets are installed.
# Usage: test_openssl.sh <pkg_folder>
set -euo pipefail

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/openssl"
ETCDIR="$PKG_FOLDER/share/acf/openssl"

if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app module dir not found: $APPDIR"
    exit 1
fi

# Core module files (upstream Makefile APP_DIST)
REQUIRED=(
    openssl-controller.lua
    openssl-model.lua
    openssl.roles
    openssl.menu
    openssl-html.lsp
    openssl-read-html.lsp
)

for name in "${REQUIRED[@]}"; do
    f="$APPDIR/$name"
    if [ ! -f "$f" ]; then
        echo "ERROR: required module file missing: $f"
        exit 1
    fi
    echo "  [ok] $name"
done

# Count .lua files (parse-check candidates)
lua_count=$(find "$APPDIR" -maxdepth 1 -name '*.lua' | wc -l)
echo "  [ok] $lua_count .lua files in app dir"

# ETC_DIST
cnf="$ETCDIR/openssl-ca-acf.cnf"
if [ ! -f "$cnf" ]; then
    echo "ERROR: required config file missing: $cnf"
    exit 1
fi
echo "  [ok] openssl-ca-acf.cnf"

echo "=== Results: 8 passed, 0 failed ==="
exit 0
