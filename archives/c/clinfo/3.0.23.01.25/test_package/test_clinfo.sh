#!/usr/bin/env bash
# test_clinfo.sh — verify clinfo binary works on HarmonyOS
# Called by test_package/conanfile.py test() method
set -euo pipefail

CLINFO_BIN="$1"

if [ -z "$CLINFO_BIN" ]; then
    echo "FAIL: clinfo binary path not provided"
    exit 1
fi

if [ ! -x "$CLINFO_BIN" ]; then
    echo "FAIL: $CLINFO_BIN not found or not executable"
    exit 1
fi

echo "[test 1/2] clinfo --version"
version_output=$("$CLINFO_BIN" --version 2>&1)
echo "$version_output"
if echo "$version_output" | grep -q "3.0.23.01.25"; then
    echo "PASS: clinfo --version reports 3.0.23.01.25"
else
    echo "FAIL: unexpected --version output"
    exit 1
fi

echo "[test 2/2] clinfo -l (enumerate platforms/devices)"
list_output=$("$CLINFO_BIN" -l 2>&1)
echo "$list_output"
# With no OpenCL ICD, clinfo prints "Number of platforms: 0" and exits 0.
# With an ICD present, it prints platform/device summaries. Either way the
# enumeration ran and produced non-empty output.
if [ -z "$list_output" ]; then
    echo "FAIL: clinfo -l produced empty output"
    exit 1
fi
echo "PASS: clinfo -l enumeration completed (exit 0)"

echo "[result] clinfo test_package: 2/2 PASS"
