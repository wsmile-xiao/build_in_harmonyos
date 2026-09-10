#!/bin/bash
# test_package/test.sh — consumer smoke test for ciwiki 3.0.5
#
# Verifies the installed `ciwiki` binary, its --version/--help output and a
# real HTTP round-trip against a temporary wiki home directory.
#
# Usage: test.sh <package_folder>
#
# NOTE: shebang uses bash (not zsh) because this script relies on bash-only
# features ($RANDOM, set -euo pipefail) and is always invoked explicitly as
# `bash test.sh` from test_package/conanfile.py.
set -euo pipefail

PKG_DIR="${1:?usage: test.sh <package_folder>}"
BIN_DIR="$PKG_DIR/bin"

# HTTP round-trip needs curl; fail fast when it is unavailable.
if ! command -v curl >/dev/null 2>&1; then
    echo "        [fail] curl is required for the HTTP round-trip assertion but was not found"
    exit 1
fi
echo "        [ok] curl available"

# Locate the installed binary (Autotools default: $prefix/bin, Conan rewrites
# prefix to package folder; try both layouts for robustness).
if [ -x "$BIN_DIR/ciwiki" ]; then
    CIWIKI="$BIN_DIR/ciwiki"
elif [ -x "$PKG_DIR/usr/bin/ciwiki" ]; then
    CIWIKI="$PKG_DIR/usr/bin/ciwiki"
else
    echo "        [fail] ciwiki binary not found under $PKG_DIR"
    exit 1
fi
echo "        [ok] ciwiki binary found: $CIWIKI"

echo "[step] ciwiki --version"
ver=$("$CIWIKI" --version 2>&1 || true)
printf '%s\n' "$ver" | grep -q "version 3.0.5" || {
    echo "        [fail] --version did not print 'version 3.0.5': got: $ver"
    exit 1
}
echo "        [ok] ciwiki --version OK: $ver"

echo "[step] ciwiki --help"
help_out=$("$CIWIKI" --help 2>&1 || true)
printf '%s\n' "$help_out" | grep -q "Usage: ciwiki" || {
    echo "        [fail] --help did not print usage"
    exit 1
}
printf '%s\n' "$help_out" | grep -q -- "--port" || {
    echo "        [fail] --help did not list --port option"
    exit 1
}
echo "        [ok] ciwiki --help OK (usage + options shown)"

echo "[step] HTTP round-trip (start server, fetch root page)"
WORK="$HOME/.ciwiki-test-$$"
mkdir -p "$WORK"
PORT=$(( (RANDOM % 20000) + 20000 ))
# ciwiki serves the wiki home; the default root of a fresh home is WikiHome.
# NOTE: do NOT pass -d (debug mode reads requests from stdin and does not
# listen on the network socket); run the normal server in the background.
"$CIWIKI" -l 127.0.0.1 -p "$PORT" -h "$WORK" >/dev/null 2>&1 &
SRV_PID=$!
# give the server a moment to bind the listening socket
sleep 1
if kill -0 "$SRV_PID" 2>/dev/null; then
    echo "        [ok] ciwiki server started (pid $SRV_PID, port $PORT)"
    body=$(curl -s -m 5 "http://127.0.0.1:$PORT/" 2>&1 || true)
    if [ -n "$body" ] && printf '%s\n' "$body" | grep -qi "html"; then
        echo "        [ok] HTTP GET / returned HTML ($(printf '%s' "$body" | wc -c) bytes)"
        RC=0
    else
        echo "        [fail] HTTP GET / returned empty/non-HTML body: ${body:0:120}"
        RC=1
    fi
    kill "$SRV_PID" 2>/dev/null || true
    wait "$SRV_PID" 2>/dev/null || true
else
    echo "        [fail] ciwiki server failed to start (port $PORT)"
    RC=1
fi
rm -rf "$WORK"

exit "$RC"
