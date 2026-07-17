#!/usr/bin/env bash
# test_package/test.sh — smoke test for convmv CLI
set -euo pipefail

echo "[test] convmv --help"
if convmv --help 2>&1 | grep -q "convmv 2.06"; then
    echo "✅ convmv --help OK"
else
    echo "❌ convmv --help failed"
    exit 1
fi

echo "[test] convmv --list"
COUNT=$(convmv --list 2>/dev/null | wc -l)
if [ "$COUNT" -gt 0 ]; then
    echo "✅ convmv --list OK ($COUNT encodings)"
else
    echo "❌ convmv --list returned no encodings"
    exit 1
fi

echo "[test] convmv --unescape"
TMPDIR=$(mktemp -d)
touch "$TMPDIR/test%20file.txt"
cd "$TMPDIR"
convmv --unescape --notest -r . 2>/dev/null || true
if [ -f "test file.txt" ]; then
    echo "✅ convmv --unescape OK (test%20file.txt → test file.txt)"
else
    echo "❌ convmv --unescape failed: file not renamed"
    exit 1
fi
cd /
rm -rf "$TMPDIR"

echo "[test] convmv smoke test: PASS"
