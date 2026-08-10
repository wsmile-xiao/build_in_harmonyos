#!/data/service/hnp/bin/bash
set -euo pipefail

# test.sh — lua-stringy test wrapper
# Called by test_package/conanfile.py test() method

echo "=== lua-stringy test ==="

# Find lua binary from the lua-stringy package
LUA_BIN="${LUA_STRINGY_ROOT}/bin/lua"
if [ ! -x "$LUA_BIN" ]; then
    echo "ERROR: lua binary not found at $LUA_BIN"
    exit 1
fi

# Set LUA_CPATH to find stringy.so
export LUA_CPATH="${LUA_STRINGY_ROOT}/lib/lua/5.4/?.so;;"

# Run the test script
"$LUA_BIN" "$(dirname "$0")/test_stringy.lua"

echo "lua-stringy OK"
