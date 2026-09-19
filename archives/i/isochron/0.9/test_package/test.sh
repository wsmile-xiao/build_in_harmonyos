#!/bin/sh
# test_package/test.sh — consumer tests for the isochron binary.
# Runs in conanrun env (resolves the packaged libmnl dependency at runtime).
# Upstream 0.9 prints usage and exits non-zero for no-args/--help; assertions
# are on the printed usage pages (real behavior), not on the exit codes.
set -eu

echo "[test] isochron (bare) prints usage page"
out=$(isochron 2>&1) || true
echo "$out" | grep -q "isochron usage:"
echo "OK: isochron usage printed"

echo "[test] isochron daemon --help prints daemon usage page"
out=$(isochron daemon --help 2>&1) || true
echo "$out" | grep -q "isochron-daemon usage:"
echo "OK: isochron-daemon usage printed"

echo "ALL CONSUMER TESTS PASSED"
