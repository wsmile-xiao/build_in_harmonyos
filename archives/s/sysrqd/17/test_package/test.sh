#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer verification for the installed sysrqd binary.
#
# Runs in the conanrun environment (PATH includes the installed sbin/).
# sysrqd parses no arguments (main(void)); expected startup behaviour:
#   non-root -> "Only root can run this program." on stderr, exit 1;
#   root w/o /etc/sysrqd.secret -> syslog error, exit 1 (pre-daemon).
# All assertions hold on both root and non-root accounts (see A5 for the
# root-only SKIP branch). timeout guards against a stray daemonize.
set -u

export PATH="$PATH:/system/bin"

fail=0
pass=0
skip=0

check_eq() { # check_eq <label> <expected> <actual>
    if [ "$2" = "$3" ]; then
        echo "PASS: $1"
        pass=$((pass + 1))
    else
        echo "FAIL: $1 (expected [$2], got [$3])"
        fail=$((fail + 1))
    fi
}

echo "--- sysrqd consumer verification ---"

SYSRQD="$(command -v sysrqd || true)"
BIN_DIR="$(dirname "$0")/../bin/sysrqd"

# A1. binary exists and is executable (either on PATH or in package sbin/).
if [ -n "$SYSRQD" ] && [ -x "$SYSRQD" ]; then
    echo "PASS: binary on PATH: $SYSRQD"
    pass=$((pass + 1))
elif [ -x "$BIN_DIR" ]; then
    SYSRQD="$BIN_DIR"
    echo "PASS: binary in package bin/: $SYSRQD"
    pass=$((pass + 1))
else
    echo "FAIL: sysrqd binary not found/executable"
    fail=$((fail + 1))
    exit 1
fi

# A2. ELF magic (first 4 bytes \x7fELF).
magic="$(od -An -tx1 -N4 "$SYSRQD" 2>/dev/null | tr -d ' \n')"
check_eq "ELF magic" "7f454c46" "$magic"

# A3. e_machine == 0xB7 (183, little-endian B7 00) => AArch64.
machine="$(od -An -tx1 -j18 -N2 "$SYSRQD" 2>/dev/null | tr -d ' \n')"
check_eq "AArch64 e_machine" "b700" "$machine"

# A4. without arguments the daemon refuses to start (exit 1) instead of
#     hanging; timeout is a safety net against unexpected daemonize.
rc=0
timeout 10 "$SYSRQD" >/dev/null 2>&1 || rc=$?
if [ "$rc" -eq 1 ]; then
    echo "PASS: no-arg startup refused with exit 1"
    pass=$((pass + 1))
else
    echo "FAIL: no-arg startup exit code expected 1, got $rc"
    fail=$((fail + 1))
fi

# A5. non-root: stderr carries the explicit refusal message.
#     (root account: expected exit 1 with no stderr output -> SKIP branch)
if [ "$(id -u)" != "0" ]; then
    err="$(timeout 10 "$SYSRQD" 2>&1 >/dev/null || true)"
    if printf '%s' "$err" | grep -q "Only root can run this program"; then
        echo "PASS: non-root refusal message on stderr"
        pass=$((pass + 1))
    else
        echo "FAIL: non-root stderr message missing, got [$err]"
        fail=$((fail + 1))
    fi
else
    echo "SKIP: running as root, non-root refusal message not applicable"
    skip=$((skip + 1))
fi

# A6. arguments are ignored (no CLI parsing); same refused exit code.
rc=0
timeout 10 "$SYSRQD" --version >/dev/null 2>&1 || rc=$?
if [ "$rc" -eq 1 ]; then
    echo "PASS: --version (unparsed arg) also refused with exit 1"
    pass=$((pass + 1))
else
    echo "FAIL: --version exit code expected 1, got $rc"
    fail=$((fail + 1))
fi

if [ "$fail" -ne 0 ]; then
    echo "sysrqd test_package: $fail assertion(s) FAILED"
    exit 1
fi
echo "sysrqd test_package: $pass/$((pass + skip)) assertions PASS ($skip skipped)"
exit 0
