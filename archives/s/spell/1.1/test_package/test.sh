#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for the spell executable
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary behavior.
set -eu

echo "[test] spell --version"
spell --version | grep -q "GNU Spell 1.1"
echo "OK: --version reports GNU Spell 1.1"

echo "[test] spell --help"
spell --help | grep -q "Usage:"
echo "OK: --help prints usage"

echo "[test] invalid option exits non-zero (getopt error path, src/spell.c exit(EXIT_FAILURE))"
if spell -Z </dev/null >/dev/null 2>&1; then
    echo "FAIL: invalid option must exit non-zero"
    exit 1
fi
echo "OK: invalid option rejected"

echo "ALL CONSUMER TESTS PASSED"
