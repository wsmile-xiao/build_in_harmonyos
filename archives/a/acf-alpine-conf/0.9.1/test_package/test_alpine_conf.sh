#!/bin/sh
set -eu

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/alpine-conf"
if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app module dir not found: $APPDIR"
    exit 1
fi

for name in \
    lbu-controller.lua \
    lbu-model.lua \
    lbu.roles \
    lbu.menu \
    lbu-listbackups-html.lsp
do
    path="$APPDIR/$name"
    if [ ! -f "$path" ]; then
        echo "ERROR: required module file missing: $path"
        exit 1
    fi
    echo "  [ok] $name"
done

echo "=== Results: 5 passed, 0 failed ==="
