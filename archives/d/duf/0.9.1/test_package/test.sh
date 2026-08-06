#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for duf executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[test] duf --version"
duf --version && echo "        [ok] --version OK" || {
    echo "[test] --version failed, trying --help..."
    duf --help > /dev/null 2>&1 && echo "        [ok] --help OK" || {
        echo "        [fail] duf failed both --version and --help"
        exit 1
    }
}
