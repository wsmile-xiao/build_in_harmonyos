#!/usr/bin/env bash
# test_package/test.sh — smoke test for axel executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] axel --version"
axel --version && echo "        [ok] --version OK" || {
    echo "        [fail] --version failed, trying --help..."
    axel --help > /dev/null 2>&1 && echo "        [ok] --help OK" || {
        echo "        [fail] axel failed both --version and --help"
        exit 1
    }
}
