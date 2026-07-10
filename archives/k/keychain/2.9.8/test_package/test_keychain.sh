#!/usr/bin/env bash
# test_keychain.sh — keychain 2.9.8 smoke test
# Usage: bash test_keychain.sh <path-to-keychain-binary>
set -euo pipefail

KEYCHAIN_BIN="${1:?Usage: bash test_keychain.sh <path-to-keychain-binary>}"

# 1. Verify the keychain script exists
if [ ! -f "$KEYCHAIN_BIN" ]; then
    echo "FAIL: keychain script not found at $KEYCHAIN_BIN"
    exit 1
fi

# 2. Syntax check (bash -n)
bash -n "$KEYCHAIN_BIN"

# 3. Version embedding check
grep -q '2.9.8' "$KEYCHAIN_BIN"

echo "keychain 2.9.8 test: OK"
