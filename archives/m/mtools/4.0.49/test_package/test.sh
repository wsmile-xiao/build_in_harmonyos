#!/data/service/hnp/bin/bash
set -euo pipefail

echo "[step] mtools --version"
mtools --version && echo "[ok] --version OK" || {
    echo "[step] --version failed, trying --help..."
    mtools --help > /dev/null 2>&1 && echo "[ok] --help OK" || {
        echo "[fail] mtools failed both --version and --help"
        exit 1
    }
}
