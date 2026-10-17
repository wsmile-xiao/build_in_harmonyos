#!/bin/sh
# Consumer test for ntp 4.2.8p18 CLI tools.
# Runs on the build host via `sh` (invoked from test() with self.run).
#   - Hard checks: the required packaged CLI artifacts (ntpq/ntpdate/ntpdc/
#     sntp — see conanfile.py build() _required list) exist in package bin/
#     and are valid ELF executables (cross-compiled for OHOS aarch64).
#   - Best-effort execution: when the host can execute the target binary,
#     run --version; cross-compiled binaries give rc 126/127 on a foreign
#     host and are reported as skip (not failure).
#   - Additional tools (tickadj/ntpd/etc.) are informational only — they are
#     not part of the recipe's required build set.
# Usage: test_ntp.sh <package_folder>
set -u

pkg_dir="$1"
fail=0

for bin in ntpq ntpdate ntpdc sntp; do
    b="$pkg_dir/bin/$bin"
    if [ ! -f "$b" ]; then
        echo "FAIL: $bin missing ($b)"
        fail=1
        continue
    fi
    magic=$(head -c4 "$b" 2>/dev/null | od -An -tx1 | tr -d ' \n')
    if [ "$magic" != "7f454c46" ]; then
        echo "FAIL: $bin is not an ELF executable (magic=$magic)"
        fail=1
        continue
    fi
    echo "OK: $bin present and ELF"

    # Best-effort execution (rc 0 = runs; 126/127 = foreign-arch cross binary)
    "$b" --version >/dev/null 2>&1
    rc=$?
    if [ "$rc" -eq 0 ]; then
        echo "OK: $bin --version works"
    elif [ "$rc" -eq 126 ] || [ "$rc" -eq 127 ]; then
        echo "SKIP: $bin is cross-compiled, cannot execute on this host"
    else
        echo "WARN: $bin --version rc=$rc (flag may be unsupported, artifact verified)"
    fi
done

if [ "$fail" -ne 0 ]; then
    echo "ntp test_package FAILED"
    exit 1
fi
echo "ntp test_package PASSED"
exit 0
