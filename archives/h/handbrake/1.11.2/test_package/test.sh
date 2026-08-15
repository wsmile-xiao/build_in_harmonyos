#!/bin/sh
# test_package/test.sh — real smoke test for HandBrakeCLI
# Runs the packaged binary path passed by test_package/conanfile.py.
set -eu

CLI="${1:-HandBrakeCLI}"

if [ ! -x "$CLI" ]; then
    echo "[test] FAIL: $CLI not found or not executable"
    exit 1
fi

echo "[test] $CLI --version"
set +e
"$CLI" --version >/dev/null 2>&1
ret=$?
set -e
if [ "$ret" -ne 0 ]; then
    echo "[test] FAIL: $CLI --version exited with $ret"
    exit 1
fi
echo "[test] OK: $CLI --version returned 0"

echo "[test] $CLI --help (sanity)"
set +e
"$CLI" --help >/dev/null 2>&1
ret=$?
set -e
if [ "$ret" -ne 0 ]; then
    echo "[test] FAIL: $CLI --help exited with $ret"
    exit 1
fi
echo "[test] OK: $CLI --help ran"
exit 0
