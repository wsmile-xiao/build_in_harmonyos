#!/usr/bin/env bash
# test_package/test.sh — smoke test for ruby-build executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] ruby-build --version"
ruby-build --version && echo "OK: --version" || {
    echo "[test] --version failed, trying --help..."
    ruby-build --help > /dev/null 2>&1 && echo "OK: --help" || {
        echo "FAIL: ruby-build failed both --version and --help"
        exit 1
    }
}
