#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for gallery-dl executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] gallery-dl --version"
gallery-dl --version && echo "[ok] --version OK" || {
    echo "[warn] --version failed, trying --help..."
    gallery-dl --help > /dev/null 2>&1 && echo "[ok] --help OK" || {
        echo "[fail] gallery-dl failed both --version and --help"
        exit 1
    }
}
