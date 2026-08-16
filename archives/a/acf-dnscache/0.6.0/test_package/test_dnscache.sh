#!/bin/sh
set -eu

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/dnscache"
if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app module dir not found: $APPDIR"
    exit 1
fi

for name in \
    dnscache-controller.lua \
    dnscache-model.lua \
    dnscache.roles \
    dnscache.menu \
    dnscache-config-html.lsp \
    dnscache-listdomains-html.lsp
do
    path="$APPDIR/$name"
    if [ ! -f "$path" ]; then
        echo "ERROR: required module file missing: $path"
        exit 1
    fi
    echo "  [ok] $name"
done

# These upstream module links point to shared ACF templates provided by
# acf-core when packages are installed into the same prefix.
for entry in \
    dnscache-expert-html.lsp:../expert-html.lsp \
    dnscache-status-html.lsp:../status-html.lsp
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

echo "=== Results: 8 passed, 0 failed ==="
