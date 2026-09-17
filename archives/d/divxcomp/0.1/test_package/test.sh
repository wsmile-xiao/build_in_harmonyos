#!/data/service/hnp/bin/bash
# test_package/test.sh — headless smoke test for divxcomp 0.1.
#
# The upstream GUI (Perl::Tk + X11) cannot run on headless OHOS; the
# portability patch adds a --version entry point (BEGIN block, before
# `use Tk`) that works headless. This test exercises the packaged
# artifact through that entry point. Runs with the package bin/ on PATH
# (VirtualRunEnv), so it fails if the package artifacts are missing.
set -uo pipefail

echo "[test] divxcomp --version"
if ! output=$(divxcomp --version 2>&1); then
    echo "FAIL: divxcomp --version exited non-zero"
    echo "$output"
    exit 1
fi
echo "$output"
if ! echo "$output" | grep -q "divxcomp 0.1"; then
    echo "FAIL: unexpected --version output"
    exit 1
fi
echo "PASS: divxcomp --version reports 0.1"
exit 0
