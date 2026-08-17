#!/bin/sh
set -eu

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/quagga"
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

for prefix in bgp ospf zebra
do
    for suffix in controller.lua model.lua menu roles details-html.lsp welcome-html.lsp
    do
        name="$prefix-$suffix"
        case "$suffix" in
            menu|roles) name="$prefix.$suffix" ;;
        esac
        path="$APPDIR/$name"
        if [ ! -f "$path" ]; then
            echo "ERROR: required module file missing: $path"
            exit 1
        fi
        echo "  [ok] $name"
    done
done

for entry in \
    bgp-expert-html.lsp:../expert-html.lsp \
    bgp-status-html.lsp:../status-html.lsp \
    ospf-expert-html.lsp:../expert-html.lsp \
    ospf-status-html.lsp:../status-html.lsp \
    zebra-expert-html.lsp:../expert-html.lsp \
    zebra-status-html.lsp:../status-html.lsp
do
    name=${entry%%:*}
    expected=${entry#*:}
    path="$APPDIR/$name"
    check_link_or_fallback "$path" "$expected" "$name"
done

echo "=== Results: 24 passed, 0 failed ==="
