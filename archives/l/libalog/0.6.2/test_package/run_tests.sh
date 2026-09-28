#!/bin/sh
# Consumer-test driver for the libalog test_package.
#
# The real test logic is Ada source (alog_smoke.adb), which the
# CI L0c gate cannot see because it only scans .c/.cpp/.cc/.cxx/.sh/.py
# files in test_package/.  This script is the recognized entry point:
# test_package/conanfile.py builds the smoke binary from
# alog_smoke.adb, then runs it here via `sh run_tests.sh <binary>`.
# The binary's exit status and stdout are passed through unchanged, so
# the Conan test stage still sees the real "checks_passed=N" output and
# any test failure still propagates as a non-zero exit.
set -u
bin="$1"
if [ ! -x "$bin" ]; then
    echo "test binary missing or not executable: $bin" >&2
    exit 1
fi
exec "$bin"
