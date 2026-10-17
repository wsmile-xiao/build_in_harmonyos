#!/usr/bin/env bash
# test_package/test.sh — smoke test for the numdiff 5.9.0 executable.
#
# Mirrors the assertions performed by test_package/conanfile.py::test().
# numdiff is a command-line tool, so the checks really execute the installed
# binary (R34): they do not merely print a string.
#
# Upstream regression suite: numdiff 5.9.0 ships no in-tree tests; the
# official suite is the separate `numdiff_tests-1.7.0` tarball.
set -euo pipefail

echo "[test] numdiff --version"
numdiff --version 2>&1 | grep -q "numdiff 5.9.0"

echo "[test] identical numeric files compare equal (exit 0)"
printf '1  2.0\n3  4.0\n' > a.txt
printf '1  2.0\n3  4.0\n' > b.txt
numdiff a.txt b.txt

echo "[test] a different numeric field is reported"
printf '1  2.0\n3  9.0\n' > c.txt
# numdiff deliberately returns a non-zero exit status as soon as it detects a
# difference, so the `|| true` below is intentional: this step asserts on the
# report CONTENTS (the grep on the next line), not on numdiff's exit code.
# This mirrors the `ignore_errors=True` used by test_package/conanfile.py.
numdiff a.txt c.txt > numdiff-report.txt || true
grep -q "9.0" numdiff-report.txt

echo "[test] companion tool ndselect is present"
ndselect --version 2>&1 | grep -q "ndselect 5.9.0"

echo "[test] numdiff smoke tests PASS"
