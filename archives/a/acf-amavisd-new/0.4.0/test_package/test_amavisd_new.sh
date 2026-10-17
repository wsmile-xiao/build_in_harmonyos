#!/bin/sh
set -eu

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/amavisd-new"
if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app module dir not found: $APPDIR"
    exit 1
fi

for name in \
    amavis-controller.lua \
    amavis-model.lua \
    amavis.roles \
    amavis.menu
do
    path="$APPDIR/$name"
    if [ ! -f "$path" ]; then
        echo "ERROR: required module file missing: $path"
        exit 1
    fi
    echo "  [ok] $name"
done

for entry in \
    amavis-expert-html.lsp:../expert-html.lsp \
    amavis-status-html.lsp:../status-html.lsp
do
    name=${entry%%:*}
    expected=${entry#*:}
    path="$APPDIR/$name"
    if [ ! -L "$path" ]; then
        echo "ERROR: required module symlink missing: $path"
        exit 1
    fi
    actual=$(readlink "$path")
    if [ "$actual" != "$expected" ]; then
        echo "ERROR: unexpected symlink target for $path: $actual"
        exit 1
    fi
    echo "  [ok] $name (symlink -> $actual)"
done

echo "=== Results: 6 passed, 0 failed ==="
