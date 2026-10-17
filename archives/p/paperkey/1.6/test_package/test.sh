#!/usr/bin/env bash
# test_package/test.sh — smoke test for paperkey binary
# Verifies paperkey --version executes and outputs expected version string.
# Called by conanfile.py test() method.
# Satisfies CI L0c gate (requires .sh/.c/.cpp/.py source file in test_package/).
set -euo pipefail

PAPERKEY_BIN="${PAPERKEY_BIN:-paperkey}"

echo "[test] Running paperkey --version"
output=$("$PAPERKEY_BIN" --version 2>&1) || {
    echo "        [fail] paperkey --version exited with non-zero status"
    exit 1
}

case "$output" in
    *paperkey*)
        echo "        [ok] paperkey --version: $output"
        ;;
    *)
        echo "        [fail] paperkey --version unexpected output: $output"
        exit 1
        ;;
esac

echo "[test] All smoke tests passed"
