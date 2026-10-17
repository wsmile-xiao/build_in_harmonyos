#!/bin/sh
set -eu

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/snort"
if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app module dir not found: $APPDIR"
    exit 1
fi

check_link_or_fallback() {
    path=$1
    expected=$2
    name=$3

    if [ -L "$path" ]; then
        actual=$(readlink "$path")
        kind="symlink ->"
    elif [ -f "$path" ]; then
        actual=$(cat "$path")
        kind="fallback file ->"
    else
        echo "ERROR: required module symlink missing: $path"
        exit 1
    fi

    if [ "$actual" != "$expected" ]; then
        echo "ERROR: unexpected symlink target for $path: $actual"
        exit 1
    fi
    echo "  [ok] $name ($kind $actual)"
}

for name in \
    snort-controller.lua \
    snort-model.lua \
    snort.roles \
    snort.menu \
    snort-details-html.lsp
do
    path="$APPDIR/$name"
    if [ ! -f "$path" ]; then
        echo "ERROR: required module file missing: $path"
        exit 1
    fi
    echo "  [ok] $name"
done

for entry in \
    snort-expert-html.lsp:../expert-html.lsp \
    snort-status-html.lsp:../status-html.lsp
do
    name=${entry%%:*}
    expected=${entry#*:}
    path="$APPDIR/$name"
    check_link_or_fallback "$path" "$expected" "$name"
done

echo "=== Results: 7 passed, 0 failed ==="
