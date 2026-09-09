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
if echo "$version_output" | grep -q "3.0.25.02.14"; then
    echo "PASS: clinfo --version reports 3.0.25.02.14"
else
    echo "FAIL: unexpected --version output"
    exit 1
fi

echo "[test 2/2] clinfo (enumerate platforms/devices)"
info_output=$("$CLINFO_BIN" 2>&1)
echo "$info_output"
# The summary invocation (`-l`) intentionally produces no text when the ICD
# loader reports zero platforms in 3.0.25.02.14. The default invocation always
# reports the platform count, so it is a stronger portable enumeration check.
if ! echo "$info_output" | grep -q "Number of platforms"; then
    echo "FAIL: clinfo output did not contain the platform count"
    exit 1
fi
echo "PASS: clinfo enumeration completed and reported the platform count"

echo "[result] clinfo test_package: 2/2 PASS"
