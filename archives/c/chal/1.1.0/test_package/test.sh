#!/bin/bash
# chal test_package — real functional smoke test (R34: must exercise the binary)
# Chal is a UCI chess engine. Feed it perft commands and verify the node counts.
# Standard chess perft values from the start position:
#   perft 1 = 20, perft 2 = 400, perft 3 = 8902, perft 4 = 197281, perft 5 = 4865609
set -e

CHAL_BIN="${CHAL_BIN:-$(command -v chal)}"
if [ -z "$CHAL_BIN" ]; then
    echo "FAIL: chal binary not found in PATH"
    exit 1
fi

echo "--- chal version ---"
printf 'uci\nquit\n' | "$CHAL_BIN" | grep -E "id name|uciok" || true

echo "--- perft 3 (expect 8902) ---"
out=$(printf 'perft 3\nquit\n' | "$CHAL_BIN")
echo "$out"
if ! echo "$out" | grep -q "perft depth 3 nodes 8902"; then
    echo "FAIL: perft 3 did not report 8902 nodes"
    exit 1
fi

echo "--- perft 4 (expect 197281) ---"
out=$(printf 'perft 4\nquit\n' | "$CHAL_BIN")
echo "$out"
if ! echo "$out" | grep -q "perft depth 4 nodes 197281"; then
    echo "FAIL: perft 4 did not report 197281 nodes"
    exit 1
fi

echo "PASS: chal perft smoke test OK"
