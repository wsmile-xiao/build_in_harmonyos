#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the daemonize executable
# Runs in conanrun env (PATH includes the installed sbin/).
# R34: genuinely exercises the packaged binary.
set -euo pipefail

echo "[step] daemonize version check"
# daemonize without arguments exits non-zero (expected behavior),
# so we capture the output without failing on the exit code.
daemonize > daemonize-output.txt 2>&1 || true

grep -q "daemonize, version 1.7.8" daemonize-output.txt || {
    echo "        [fail] daemonize did not print expected version string"
    exit 1
}

echo "[step] daemonize help output"
grep -q "Usage: daemonize" daemonize-output.txt || {
    echo "        [fail] daemonize did not print usage line"
    exit 1
}

echo "        [ok] daemonize binary is functional"
