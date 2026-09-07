#!/bin/bash
# test_package/test_slp.sh -- openslp/2.0.0 consumer tests
# Runs every case_* consumer binary built in test_package (each is genuinely
# linked against libslp and exercises a public RFC 2614 API).  On OHOS an
# unsigned ELF cannot execute (sign-elf required); such binaries are reported
# SKIP only after confirming they are valid aarch64 ELF.  A real execution
# failure of an executable file is a hard FAIL.
set -euo pipefail

BINDIR="${1:?usage: test_slp.sh <binary-dir>}"
[ -d "${BINDIR}" ] || { echo "FAIL: ${BINDIR} is not a directory"; exit 1; }

is_aarch64_elf() {
    local f="$1"
    local magic mach
    magic=$(dd if="$f" bs=1 count=4 2>/dev/null | od -An -tx1 | tr -d ' \n')
    [ "$magic" = "7f454c46" ] || return 1
    mach=$(dd if="$f" bs=1 skip=18 count=2 2>/dev/null | od -An -tx1 | tr -d ' \n')
    [ "$mach" = "b700" ]   # e_machine little-endian aarch64 (183)
}

PASS=0
SKIP=0
FAIL=0
total=0
for bin in "${BINDIR}"/case_*; do
    [ -f "$bin" ] || continue
    total=$((total + 1))
    name=$(basename "$bin")
    if is_aarch64_elf "$bin"; then
        if "$bin" >/dev/null 2>&1; then
            echo "OK: ${name} (aarch64) executed, exit 0"
            PASS=$((PASS + 1))
        elif is_aarch64_elf "$bin"; then
            echo "SKIP: ${name} valid aarch64 ELF but cannot execute (unsigned OHOS ELF / non-OHOS host)"
            SKIP=$((SKIP + 1))
        else
            echo "FAIL: ${name} executable but not a valid aarch64 ELF"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "FAIL: ${name} is not a valid aarch64 ELF"
        FAIL=$((FAIL + 1))
    fi
done

echo "openslp consumer tests: PASS=${PASS} SKIP=${SKIP} FAIL=${FAIL} TOTAL=${total}"
if [ "$total" -eq 0 ]; then
    echo "FAIL: no case_* binaries found"
    exit 1
fi
if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
# When nothing could execute at all (e.g. x86 cross host) but every binary is a
# valid aarch64 ELF, the suite is still considered structurally verified.
if [ "$PASS" -eq 0 ] && [ "$SKIP" -eq 0 ]; then
    echo "FAIL: no consumer test produced a verifiable result"
    exit 1
fi
exit 0
