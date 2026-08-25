#!/bin/bash
# test_package/test.sh — smoke test for facad executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] facad --version"
facad --version && echo "✅ --version OK" || {
    echo "[test] --version failed, trying --help..."
    facad --help > /dev/null 2>&1 && echo "✅ --help OK" || {
        echo "❌ facad failed both --version and --help"
        exit 1
    }
}
