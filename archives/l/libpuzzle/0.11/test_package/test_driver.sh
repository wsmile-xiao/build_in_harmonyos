#!/bin/sh
# test_driver.sh — libpuzzle 0.11 consumer driver (POSIX sh).
# Runs the C API test binary plus the puzzle-diff CLI smoke test, then
# prints the single HMBS_TEST_PACKAGE_RESULT marker for the hard gate.
# Args: $1 = test binary, $2 = puzzle-diff binary, $3 = work dir.
set -u

TEST_BIN="$1"
PUZZLE_DIFF="$2"
WORKDIR="$3"
mkdir -p "$WORKDIR"

discovered=7
failed=0

"$TEST_BIN" "$WORKDIR"
c_rc=$?
if [ "$c_rc" -gt 6 ]; then
    c_rc=6
fi
failed=$((failed + c_rc))
if [ "$c_rc" -eq 0 ]; then
    echo "[ok] C API 6/6 cases passed"
else
    echo "[fail] C API failed cases: $c_rc"
fi

# puzzle-diff -e exits 10 when the pair looks similar (upstream contract).
"$PUZZLE_DIFF" -e "$WORKDIR/t1.png" "$WORKDIR/t2.png" >/dev/null 2>&1
cli_rc=$?
if [ "$cli_rc" -eq 10 ]; then
    echo "[ok] puzzle-diff -e similar pair exit=10"
else
    echo "[fail] puzzle-diff -e exit=$cli_rc (expected 10)"
    failed=$((failed + 1))
fi

passed=$((discovered - failed))
if [ "$failed" -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"sh test_driver.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"sh test_driver.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
    exit 1
fi
