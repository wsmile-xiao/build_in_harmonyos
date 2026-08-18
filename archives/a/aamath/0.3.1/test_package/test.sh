#!/usr/bin/env bash
# test_package/test.sh — smoke test for aamath executable
# aamath renders math expressions as ASCII art text.
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] aamath -h (version/help check)"
aamath -h > /dev/null 2>&1 && echo "PASS: aamath -h OK" || {
    echo "[test] -h failed, trying pipe test..."
    echo "1+1" | aamath -q > /dev/null 2>&1 && echo "PASS: aamath pipe OK" || {
        echo "FAIL: aamath failed both -h and pipe test"
        exit 1
    }
}

echo "[test] aamath pipe render test"
output=$(echo "1+1" | aamath -q 2>&1)
if [ -n "$output" ]; then
    echo "PASS: aamath rendered expression"
else
    echo "FAIL: aamath produced empty output"
    exit 1
fi
