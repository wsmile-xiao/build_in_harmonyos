#!/usr/bin/env bash
# test.sh — wbox 5 client-side smoke test (consumer view).
#
# Upstream wbox ships no test suite (see test_package/MANIFEST.yml for the
# inventory evidence), so the consumer-side smoke test checks the two stable,
# documented entry points of the CLI contract:
#   1. `wbox -v`       -> "WBox version 5"
#   2. `wbox` (no url) -> the usage/help banner
#
# usage: test.sh [path-to-wbox-binary]
set -euo pipefail

WBOX_BIN="${1:-${WBOX_BIN:-wbox}}"
echo "== wbox smoke test =="
echo "binary: $WBOX_BIN"

# 1. version banner
version_out=$("$WBOX_BIN" -v 2>&1)
echo "$version_out"
expected="WBox version 5"
if [ "$version_out" != "$expected" ]; then
    echo "FAIL: expected '$expected', got '$version_out'"
    exit 1
fi
echo "PASS: version banner"

# 2. usage banner when no URL is given
usage_out=$("$WBOX_BIN" 2>&1 || true)
echo "$usage_out" | head -3
if ! echo "$usage_out" | grep -q "Usage: wbox <url>"; then
    echo "FAIL: usage banner missing"
    exit 1
fi
echo "PASS: usage banner"

echo "== smoke test PASSED =="
