#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gdu executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] gdu --version"
gdu --version && echo "        [ok] --version OK" || {
    echo "        [step] --version failed, trying --help..."
    gdu --help > /dev/null 2>&1 && echo "        [ok] --help OK" || {
        echo "        [fail] gdu failed both --version and --help"
        exit 1
    }
}
