#!/usr/bin/env bash
# test_rbenv_bundler.sh — Test script for rbenv-bundler Conan package
# Verifies package contents, script syntax, and functionality
set -euo pipefail

BIN_PATH="${1:-bin/rbenv-bundler}"
INCLUDES_PATH="${2:-etc/rbenv.d/bundler/includes.sh}"

echo "=== rbenv-bundler test suite ==="

echo "[1/4] Verify binary exists..."
if [ ! -f "$BIN_PATH" ]; then
    echo "FAIL: rbenv-bundler not found at $BIN_PATH"
    exit 1
fi
echo "PASS: binary exists"

echo "[2/4] Verify includes.sh exists..."
if [ ! -f "$INCLUDES_PATH" ]; then
    echo "FAIL: includes.sh not found at $INCLUDES_PATH"
    exit 1
fi
echo "PASS: includes.sh exists"

echo "[3/4] Bash syntax check..."
bash -n "$BIN_PATH" || { echo "FAIL: syntax error in rbenv-bundler"; exit 1; }
bash -n "$INCLUDES_PATH" || { echo "FAIL: syntax error in includes.sh"; exit 1; }
echo "PASS: syntax valid"

echo "[4/4] Verify HarmonyOS patch applied..."
if ! grep -q "HarmonyOS" "$INCLUDES_PATH"; then
    echo "FAIL: HarmonyOS not found in includes.sh (patch not applied)"
    exit 1
fi
echo "PASS: HarmonyOS patch applied"

echo "=== All tests passed ==="
