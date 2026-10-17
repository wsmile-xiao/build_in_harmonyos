#!/bin/sh
# test.sh — L0c-compliant test runner for lpeg 1.1.0
# R34: Actually tests lpeg's pattern matching API via Lua
#
# This script downloads and builds Lua, then runs test.lua which exercises
# lpeg's P, R, S, C, match, and version API with 15 assertions.
#
# Usage: ./test.sh [LPEG_SO_PATH] [LUA_SOURCE_DIR]

set -e

LPEG_SO="${1:-./lpeg.so}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_LUA="$SCRIPT_DIR/test.lua"

# Find or build Lua
LUA_BIN="${LUA:-$(command -v lua 2>/dev/null)}"

if [ -z "$LUA_BIN" ]; then
    echo "Lua not found, building from source..."
    LUA_URL="https://www.lua.org/ftp/lua-5.4.7.tar.gz"
    LUA_TAR="$SCRIPT_DIR/lua-5.4.7.tar.gz"
    LUA_DIR="$SCRIPT_DIR/lua-5.4.7"

    curl -sL -o "$LUA_TAR" "$LUA_URL"
    tar xzf "$LUA_TAR" -C "$SCRIPT_DIR"
    make -C "$LUA_DIR" linux CC=clang MYCFLAGS="-fPIC -O2"
    LUA_BIN="$LUA_DIR/src/lua"
fi

# Run the lpeg test suite
echo "Running lpeg test suite..."
LUA_CPATH="$(dirname "$LPEG_SO")/?.so" "$LUA_BIN" "$TEST_LUA"

echo "lpeg test: PASSED"
