#!/bin/sh
set -eu

PKG_FOLDER="${1:-}"
if [ -z "$PKG_FOLDER" ]; then
    echo "ERROR: package folder path is required"
    exit 1
fi

MODULE="$PKG_FOLDER/share/lua/5.3/aconf/modules/network.lua"
if [ ! -f "$MODULE" ]; then
    echo "ERROR: module file missing: $MODULE"
    exit 1
fi
SIZE=$(wc -c < "$MODULE")
echo "  [ok] network.lua present ($SIZE bytes)"

LUA_BIN=""
for c in lua lua5.3 luac luac5.3; do
    if command -v "$c" >/dev/null 2>&1; then
        LUA_BIN="$c"
        break
    fi
done

if [ -n "$LUA_BIN" ]; then
    case "$LUA_BIN" in
        luac*)
            "$LUA_BIN" -p "$MODULE"
            ;;
        *)
            "$LUA_BIN" -e "assert(loadfile(arg[1]))" "$MODULE"
            ;;
    esac
    echo "  [ok] lua syntax check passed ($LUA_BIN)"
else
    echo "  [warn] Lua interpreter not found; file presence smoke passed"
fi

echo "=== Results: passed ==="
