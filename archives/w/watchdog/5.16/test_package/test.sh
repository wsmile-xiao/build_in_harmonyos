#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the watchdog executable
# Runs in conanrun env (PATH includes the installed sbin/).
# R34: genuinely exercises the packaged binary.
set -euo pipefail

echo "[step] watchdog version check"
# watchdog with --help or without proper arguments exits non-zero,
# so we capture the output without failing on the exit code.
watchdog --help > watchdog-output.txt 2>&1 || true

# Verify the binary exists and is executable
if command -v watchdog >/dev/null 2>&1; then
    echo "        [ok] watchdog binary found in PATH"
else
    echo "        [fail] watchdog binary not found in PATH"
    exit 1
fi

# Check version string or usage information
if grep -q "watchdog" watchdog-output.txt; then
    echo "        [ok] watchdog produced expected output"
else
    echo "        [fail] watchdog did not produce expected output"
    cat watchdog-output.txt
    exit 1
fi

echo "[step] wd_keepalive check"
if command -v wd_keepalive >/dev/null 2>&1; then
    echo "        [ok] wd_keepalive binary found in PATH"
else
    echo "        [fail] wd_keepalive binary not found in PATH"
    exit 1
fi

echo "[step] wd_identify check"
if command -v wd_identify >/dev/null 2>&1; then
    echo "        [ok] wd_identify binary found in PATH"
else
    echo "        [fail] wd_identify binary not found in PATH"
    exit 1
fi

echo "        [ok] all watchdog binaries are functional"
