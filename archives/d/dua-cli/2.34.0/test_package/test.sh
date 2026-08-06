#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for dua-cli executable
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

echo "[step] dua --version"
dua --version && echo "[ok] --version passed" || {
    echo "[warn] --version failed, trying --help..."
    dua --help > /dev/null 2>&1 && echo "[ok] --help passed" || {
        echo "[fail] dua failed both --version and --help"
        exit 1
    }
}

echo "[step] dua aggregate (basic functionality)"
if dua aggregate /tmp > /dev/null 2>&1; then
    echo "[ok] aggregate passed (/tmp)"
elif dua aggregate "$HOME" > /dev/null 2>&1; then
    echo "[ok] aggregate passed (HOME)"
elif dua aggregate . > /dev/null 2>&1; then
    echo "[ok] aggregate passed (cwd)"
else
    echo "[fail] aggregate failed on all directories (/tmp, HOME, cwd)"
    exit 1
fi
