#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for ripmime executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] ripmime --version"
ripmime --version && echo "        [ok] --version OK" || {
    echo "        [warn] --version failed, trying --help..."
    ripmime --help > /dev/null 2>&1 && echo "        [ok] --help OK" || {
        echo "        [fail] ripmime failed both --version and --help"
        exit 1
    }
}
