#!/usr/bin/env bash
# test_package/test.sh — cksfv 1.3.15 smoke test
# Usage: test.sh <cksfv-binary>
set -euo pipefail

CKSFV="${1:?cksfv binary path required}"
FAILED=0

TMPDIR_WORK="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_WORK"' EXIT

cd "$TMPDIR_WORK"
echo "Hello, cksfv!"  > hello.txt
echo "World of checksums." > world.txt

# Test 1: create SFV listing
if ! "$CKSFV" hello.txt world.txt > test.sfv 2>/dev/null; then
    echo "FAIL: SFV creation failed"
    FAILED=1
fi

# Test 2: verify SFV listing
if ! "$CKSFV" -f test.sfv >/dev/null 2>/dev/null; then
    echo "FAIL: SFV verification failed"
    FAILED=1
fi

if [ "$FAILED" -eq 0 ]; then
    echo "PASS: cksfv smoke test (create + verify)"
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"discovered":1,"command":"bash test.sh <cksfv_binary>"}'
else
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"discovered":1,"command":"bash test.sh <cksfv_binary>"}'
fi
exit "$FAILED"
