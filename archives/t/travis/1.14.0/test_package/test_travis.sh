#!/bin/sh
set -euo pipefail
# Suppress SIGPIPE so an early reader (e.g. CI log pipeline | head) cannot
# kill the script with exit 141 before it prints its summary line.
trap '' PIPE

PKG_DIR="$1"
TRAVIS_BIN="$PKG_DIR/bin/travis"

if [ ! -f "$TRAVIS_BIN" ]; then
    echo "ERROR: travis binary not found at $TRAVIS_BIN"
    exit 1
fi

if [ ! -x "$TRAVIS_BIN" ]; then
    echo "ERROR: travis binary is not executable"
    exit 1
fi

if ! grep -F 'echo "travis 1.14.0"' "$TRAVIS_BIN" >/dev/null 2>&1; then
    echo "ERROR: wrapper does not provide an offline version fast-path"
    exit 1
fi

VERSION_OUTPUT="$("$TRAVIS_BIN" version)"
echo "$VERSION_OUTPUT"
[ "$VERSION_OUTPUT" = "travis 1.14.0" ]

[ "$("$TRAVIS_BIN" --version)" = "travis 1.14.0" ]
[ "$("$TRAVIS_BIN" -v)" = "travis 1.14.0" ]

# The version fast path must remain usable when Ruby and other host tools are
# absent. The absolute shebang still starts /bin/sh with this empty PATH.
[ "$(PATH=/nonexistent "$TRAVIS_BIN" version)" = "travis 1.14.0" ]

echo "Offline smoke tests: 7/7 passed (100%)"
