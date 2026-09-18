#!/bin/sh
# Smoke test for kodi-tools binaries on target.
# Verifies each binary exists, executes, and prints its usage banner.
set -e
BINDIR="$1"
if [ -z "$BINDIR" ]; then
    echo "usage: $0 <bindir>" >&2
    exit 2
fi

fail=0

# TexturePacker: prints usage banner on -help
if [ ! -x "$BINDIR/TexturePacker" ]; then
    echo "FAIL: TexturePacker not found/executable in $BINDIR" >&2
    fail=1
else
    out=$("$BINDIR/TexturePacker" -help 2>&1 || true)
    echo "$out" | grep -q "Usage" || { echo "FAIL: TexturePacker did not print usage" >&2; fail=1; }
    echo "TexturePacker ok"
fi

# JsonSchemaBuilder: prints usage banner when invoked without args
if [ ! -x "$BINDIR/JsonSchemaBuilder" ]; then
    echo "FAIL: JsonSchemaBuilder not found/executable in $BINDIR" >&2
    fail=1
else
    out=$("$BINDIR/JsonSchemaBuilder" 2>&1 || true)
    echo "$out" | grep -qiE "usage|schema" || { echo "FAIL: JsonSchemaBuilder did not print usage" >&2; fail=1; }
    echo "JsonSchemaBuilder ok"
fi

[ "$fail" -eq 0 ] && echo "smoke test passed"
exit $fail
