#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ttyplot executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] ttyplot -v"
ttyplot -v && echo "✅ -v OK" || {
    echo "[test] -v failed, trying -h..."
    ttyplot -h > /dev/null 2>&1 && echo "✅ -h OK" || {
        echo "❌ ttyplot failed both -v and -h"
        exit 1
    }
}
