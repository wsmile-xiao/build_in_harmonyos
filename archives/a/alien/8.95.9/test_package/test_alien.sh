#!/usr/bin/env bash
# test_package/test_alien.sh — smoke test for alien executable
# alien converts package formats (rpm/dpkg/slp/tgz). Runs in conanrun env.
set -euo pipefail
pkg="$1"

echo "[test] alien --version"
perl -I "$pkg/lib" "$pkg/bin/alien" --version > /dev/null 2>&1 && echo "PASS: alien --version OK" || {
    echo "FAIL: alien --version"; exit 1
}

echo "[test] alien --help"
perl -I "$pkg/lib" "$pkg/bin/alien" --help > /dev/null 2>&1 || true
echo "PASS: alien smoke test OK"
