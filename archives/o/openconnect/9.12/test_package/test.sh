#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the openconnect CLI
# Runs in the conanrun env (PATH includes the installed bin/ of the package).
set -eu

echo "[test] openconnect --version"
openconnect --version

echo "[test] openconnect --help"
# openconnect prints usage on --help but exits with code 1 (missing <server>),
# so validate by content, not exit status.
help_out="$(openconnect --help 2>&1 || true)"
echo "$help_out" | grep -q "Usage:  openconnect" || {
    echo "[test] --help output missing usage line"
    exit 1
}
echo "[test] --help OK"

echo "[test] openconnect OK"
