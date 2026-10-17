#!/usr/bin/env bash
# test_package/test.sh — smoke test for lua-resty-http
# Verifies that the Lua module files are present and contain expected content
set -euo pipefail

# Get the package directory from CONAN_PACKAGE_DIR (set by conanrun env)
PKG_DIR="${CONAN_PACKAGE_DIR:-$(conanrun pwd 2>/dev/null || echo $HOME)}"
RESTY_DIR="$PKG_DIR/lib/lua/5.4/resty"

echo "[test] Checking Lua module files in $RESTY_DIR"

for f in http.lua http_connect.lua http_headers.lua; do
    if [ -f "$RESTY_DIR/$f" ]; then
        echo "✅ Found: $f ($(wc -c < "$RESTY_DIR/$f") bytes)"
    else
        echo "❌ Missing: $RESTY_DIR/$f"
        exit 1
    fi
done

# Verify content of http.lua
if grep -q "resty.http" "$RESTY_DIR/http.lua"; then
    echo "✅ http.lua contains 'resty.http' module definition"
else
    echo "❌ http.lua missing 'resty.http' module definition"
    exit 1
fi

echo "[test] lua-resty-http smoke test: PASS"
