#!/usr/bin/env bash
# test_package/test.sh — smoke test for diamond CLI
set -euo pipefail

echo "[test] diamond --version"
diamond --version && echo "✅ diamond --version OK" || {
    echo "❌ diamond --version failed"
    exit 1
}

echo "[test] diamond test (regression suite)"
diamond test && echo "✅ diamond test OK" || {
    echo "❌ diamond test failed"
    exit 1
}

echo "[test] diamond smoke test: PASS"