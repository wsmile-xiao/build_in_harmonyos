#!/usr/bin/env bash
# test_package/test.sh — smoke test for cargo-nextest executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] cargo-nextest --version"
cargo-nextest --version && echo "[ok] --version OK" || {
    echo "[step] --version failed, trying --help..."
    cargo-nextest --help > /dev/null 2>&1 && echo "[ok] --help OK" || {
        echo "[fail] cargo-nextest failed both --version and --help"
        exit 1
    }
}
