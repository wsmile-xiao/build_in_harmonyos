#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for arp-scan executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] arp-scan --version"
arp-scan --version && echo "        [ok] --version" || {
    echo "[step] --version failed, trying --help..."
    arp-scan --help > /dev/null 2>&1 && echo "        [ok] --help" || {
        echo "        [fail] arp-scan failed both --version and --help"
        exit 1
    }
}
