#!/bin/sh
# test_psmisc.sh — Smoke test for psmisc binaries
# Runs pstree and killall --version to verify they execute correctly.

# Test 1: pstree --version (exercises ncurses-linked binary)
pstree --version > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Test 1 (pstree --version): PASS"
else
    echo "Test 1 (pstree --version): FAIL"
    exit 1
fi

# Test 2: killall --version (exercises basic binary)
killall --version > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "Test 2 (killall --version): PASS"
else
    echo "Test 2 (killall --version): FAIL"
    exit 1
fi

echo "All smoke tests completed."
