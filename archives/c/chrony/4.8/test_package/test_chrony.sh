#!/bin/bash
# test_chrony.sh — host-side verification of packaged chrony binaries
# Called by test_package/conanfile.py test() method.
#
# chrony is cross-compiled for OHOS aarch64 and cannot be executed on the
# x86 CI worker (Exec format error). Verify presence + ELF magic instead.
# chronyd installs to sbin (chrony SBINDIR), chronyc to bin — the caller
# passes the actual paths found in the package.

set -euo pipefail

found=0
for bin in "$@"; do
    if [ -f "$bin" ]; then
        if head -c 4 "$bin" | grep -q $'\x7fELF'; then
            echo "PASS: $bin is a valid ELF binary"
            found=1
        else
            echo "FAIL: $bin is not an ELF binary" >&2
            exit 1
        fi
    else
        echo "WARN: $bin not found (skipped)" >&2
    fi
done

if [ "$found" -eq 0 ]; then
    echo "FAIL: none of the expected chrony binaries found: $*" >&2
    exit 1
fi

echo "chrony test_package: packaged binaries verified (cross-compile, no run)"
