#!/bin/sh
# test_typioca.sh — consumer smoke test for the packaged typioca executable.
#
# Asserts (6 shell assertions):
#   1. `typioca --version` exits 0
#   2. version output contains "typioca"
#   3. version output contains the packaged version "3.1.0"
#   4. `typioca --help` lists the root command surface ("Usage:")
#   5. `typioca --help` lists the "serve" subcommand
#   6. an unknown command exits non-zero (fails closed)
#
# The HarmonyOS-specific assertion (signed ELF / .codesign) is performed in
# test_package/conanfile.py where settings.os is known.
set -eu

# Run from a writable cwd (HMBS injects TMPDIR); avoids HMDFS getcwd issues.
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-typioca>" >&2
    exit 2
fi

BIN="$1"
if [ ! -f "$BIN" ]; then
    echo "typioca binary not found: $BIN" >&2
    exit 1
fi

echo "[step] typioca --version"
VER="$("$BIN" --version 2>&1)"
echo "        output: $VER"
printf '%s\n' "$VER" | grep -F "typioca" >/dev/null
echo "        [ok] output mentions typioca"
printf '%s\n' "$VER" | grep -F "3.1.0" >/dev/null
echo "        [ok] output reports version 3.1.0"

echo "[step] typioca --help"
HELP="$("$BIN" --help 2>&1)"
printf '%s\n' "$HELP" | grep -F "Usage:" >/dev/null
echo "        [ok] help has Usage:"
printf '%s\n' "$HELP" | grep -F "serve" >/dev/null
echo "        [ok] help lists the serve subcommand"

echo "[step] typioca serve --help"
SHELP="$("$BIN" serve --help 2>&1)"
printf '%s\n' "$SHELP" | grep -F -- "--port" >/dev/null
echo "        [ok] serve help lists --port"

echo "[step] unknown command fails closed"
if "$BIN" definitely-not-a-command >/dev/null 2>&1; then
    echo "        [FAIL] unknown command unexpectedly succeeded" >&2
    exit 1
fi
echo "        [ok] unknown command exits non-zero"

echo "[ok] all typioca smoke assertions passed"
