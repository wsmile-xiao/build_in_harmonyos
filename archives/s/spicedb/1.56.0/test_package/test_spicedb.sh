#!/bin/sh
# test_package consumer script for spicedb 1.56.0.
# Usage: test_spicedb.sh <path-to-spicedb-binary>
# Runs 3 real consumer assertions against the packaged CLI:
#   1) `version` reports 1.56.0
#   2) `--help` lists the `serve` command
#   3) `serve --help` prints gRPC/SpiceDB usage
# Exits 0 only if every assertion passes.

set -e

BIN="$1"
if [ -z "$BIN" ] || [ ! -f "$BIN" ]; then
    echo "test_spicedb: spicedb binary not found: $BIN" >&2
    exit 127
fi

fail=0

echo "test_spicedb: [1/3] spicedb version"
if OUT=$("$BIN" version 2>&1); then
    if printf '%s' "$OUT" | grep -q "1.56.0"; then
        echo "  PASS: version reports 1.56.0"
    else
        echo "  FAIL: version output lacks 1.56.0:" >&2
        printf '%s\n' "$OUT" >&2
        fail=1
    fi
else
    echo "  FAIL: spicedb version exited non-zero" >&2
    printf '%s\n' "$OUT" >&2
    fail=1
fi

echo "test_spicedb: [2/3] spicedb --help"
if OUT=$("$BIN" --help 2>&1); then
    if printf '%s' "$OUT" | grep -q "serve"; then
        echo "  PASS: --help lists serve command"
    else
        echo "  FAIL: --help does not mention serve" >&2
        fail=1
    fi
else
    echo "  FAIL: spicedb --help exited non-zero" >&2
    printf '%s\n' "$OUT" >&2
    fail=1
fi

echo "test_spicedb: [3/3] spicedb serve --help"
if OUT=$("$BIN" serve --help 2>&1); then
    if printf '%s' "$OUT" | grep -qiE "SpiceDB|gRPC"; then
        echo "  PASS: serve --help prints gRPC/SpiceDB usage"
    else
        echo "  FAIL: serve --help content unexpected" >&2
        printf '%s\n' "$OUT" >&2
        fail=1
    fi
else
    echo "  FAIL: spicedb serve --help exited non-zero" >&2
    printf '%s\n' "$OUT" >&2
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "test_spicedb: RESULT FAIL" >&2
    exit 1
fi
echo "test_spicedb: RESULT PASS (3/3)"
exit 0