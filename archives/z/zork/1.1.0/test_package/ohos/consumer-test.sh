#!/bin/sh
# OHOS consumer test case for zork/1.1.0
# Verifies the zork binary is executable and produces expected output

set -e

ZORK_BIN="${1:-zork}"

echo "=== OHOS Consumer Test: zork/1.1.0 ==="
echo "Binary: $ZORK_BIN"

# Test 1: Resolve bare command name via PATH, then check executability
if [ "$ZORK_BIN" = "${ZORK_BIN#/}" ]; then
    # No slash — bare name, resolve via PATH
    ZORK_BIN="$(command -v "$ZORK_BIN" 2>/dev/null)" || {
        echo "FAIL: zork binary not found in PATH"
        exit 1
    }
fi

if [ ! -x "$ZORK_BIN" ]; then
    echo "FAIL: zork binary not found or not executable"
    exit 1
fi
echo "PASS: zork binary is executable"

# Test 2: Run smoke test (same as upstream CI)
# '|| rc=$?' suppresses errexit for the command substitution so the
# explicit rc check below can execute and print diagnostics on failure.
output=$(printf "LOOK\nQUIT\nY\n" | timeout 10 "$ZORK_BIN" 2>&1) || rc=$?
rc=${rc:-0}

if [ "$rc" -ne 0 ]; then
    echo "FAIL: zork exited with code $rc"
    exit 1
fi

# Test 3: Verify expected output
echo "$output" | grep -q "Welcome to Dungeon" || { echo "FAIL: missing 'Welcome to Dungeon'"; exit 1; }
echo "PASS: Welcome to Dungeon"

echo "$output" | grep -q "white house" || { echo "FAIL: missing 'white house'"; exit 1; }
echo "PASS: white house"

echo "$output" | grep -q "mailbox" || { echo "FAIL: missing 'mailbox'"; exit 1; }
echo "PASS: mailbox"

echo "$output" | grep -q "game is over" || { echo "FAIL: missing 'game is over'"; exit 1; }
echo "PASS: game is over"

echo "=== All OHOS consumer tests passed ==="
exit 0
