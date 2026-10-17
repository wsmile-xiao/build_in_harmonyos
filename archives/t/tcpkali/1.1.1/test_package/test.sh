#!/bin/sh
# test_package/test.sh — smoke test for tcpkali executable
set -eu
# Enable pipefail if the shell supports it (bash, dash)
(set -o pipefail) 2>/dev/null && set -o pipefail

echo "[test] tcpkali --version"
tcpkali --version && echo "[ok] --version output verified" || {
    echo "[fail] tcpkali --version failed"
    exit 1
}
