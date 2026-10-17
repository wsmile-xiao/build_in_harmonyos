#!/usr/bin/env bash
# test_package/test.sh — smoke test for bison
set -eu

echo "[test] bison --version"
bison --version && echo "OK" || {
    echo "[test] --version failed, trying --help..."
    bison --help > /dev/null 2>&1 && echo "OK" || {
        echo "FAIL: bison failed"
        exit 1
    }
}
