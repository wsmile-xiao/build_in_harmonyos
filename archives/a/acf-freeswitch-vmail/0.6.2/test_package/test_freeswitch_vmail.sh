#!/bin/sh
set -eu

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

APPDIR="$PKG_FOLDER/share/acf/app/freeswitch-vmail"
LIBDIR="$PKG_FOLDER/share/acf/lib"
if [ ! -d "$APPDIR" ]; then
    echo "ERROR: ACF app module dir not found: $APPDIR"
    exit 1
fi
if [ ! -d "$LIBDIR" ]; then
    echo "ERROR: ACF lib dir not found: $LIBDIR"
    exit 1
fi

for name in \
    vmail-controller.lua \
    vmail-model.lua \
    vmail.roles \
    vmail.menu \
    vmail-listmessages-html.lsp \
    vmail-listusers-html.lsp \
    template-processdialplanxml-xml.lsp \
    template-processdirectoryxml-xml.lsp
do
    path="$APPDIR/$name"
    if [ ! -f "$path" ]; then
        echo "ERROR: required module file missing: $path"
        exit 1
    fi
    echo "  [ok] $name"
done

libfile="$LIBDIR/authenticator-freeswitch-vmail.lua"
if [ ! -f "$libfile" ]; then
    echo "ERROR: required ACF lib file missing: $libfile"
    exit 1
fi
echo "  [ok] authenticator-freeswitch-vmail.lua"

for entry in \
    vmail-editusers-html.lsp:vmail-listusers-html.lsp \
    vmail-listmymessages-html.lsp:vmail-listmessages-html.lsp
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

echo "=== Results: 11 passed, 0 failed ==="
