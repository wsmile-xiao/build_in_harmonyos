#!/data/service/hnp/bin/bash
set -euo pipefail

echo "[test] altermime --version"
altermime --version && echo "OK --version" || {
    echo "[test] --version failed, trying --help..."
    altermime --help > /dev/null 2>&1 && echo "OK --help" || {
        echo "FAIL altermime failed both --version and --help"
        exit 1
    }
}
