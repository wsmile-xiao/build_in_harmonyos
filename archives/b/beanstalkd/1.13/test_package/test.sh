#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for beanstalkd executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] beanstalkd -v"
beanstalkd -v && echo "✅ -v OK" || {
    echo "[test] -v failed, trying -h..."
    beanstalkd -h > /dev/null 2>&1 && echo "✅ -h OK" || {
        echo "❌ beanstalkd failed both -v and -h"
        exit 1
    }
}
