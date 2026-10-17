#!/data/service/hnp/bin/bash
set -euo pipefail

echo "[test] advscan --version"
advscan --version && echo "OK advscan --version" || {
    echo "FAIL advscan --version failed"
    exit 1
}

echo "[test] advdiff --version"
advdiff --version && echo "OK advdiff --version" || {
    echo "FAIL advdiff --version failed"
    exit 1
}
