#!/usr/bin/env bash
# test_package/test.sh — consumer test for the packaged tlshd binary.
#
# Runs in the conanrun environment (the package's sbin/ directory is on PATH
# and the transitive runtime libs are on LD_LIBRARY_PATH). Every check is a
# real assertion against the packaged binary. Cases 6 and 7 are negative
# controls asserting that invalid invocation is rejected. Only user-space code
# paths are exercised — tlshd --version and --help return before reaching the
# kernel net/handshake dispatch, and the config-file and option-error paths
# likewise abort inside the daemon's own parsing routines.
set -euo pipefail

T=${TLSHD_BIN:-tlshd}
ASSERTIONS=0
FAILURES=0

pass() { ASSERTIONS=$((ASSERTIONS + 1)); echo "PASS: $1"; }
fail() { ASSERTIONS=$((ASSERTIONS + 1)); FAILURES=$((FAILURES + 1)); echo "FAIL: $1"; }
check_contains() { # <description> <haystack> <needle>
    case "$2" in
        *"$3"*) pass "$1" ;;
        *) fail "$1 (missing substring '$3' in: $2)" ;;
    esac
}

# 0. precheck: the packaged binary is on PATH and executable
if command -v "$T" >/dev/null 2>&1 && [ -x "$(command -v "$T")" ]; then
    pass "tlshd found on PATH and executable"
else
    fail "tlshd not found on PATH"
    echo "ASSERTIONS: $ASSERTIONS, FAILURES: $FAILURES"
    exit 1
fi

# 1. tlshd --version exits 0
if ver=$("$T" --version 2>&1); then
    pass "tlshd --version exits 0"
else
    ver=""
    fail "tlshd --version did not exit 0"
fi

# 2. tlshd --version reports the packaged upstream version string
check_contains "tlshd --version carries 'ktls-utils 1.4.0'" "$ver" "ktls-utils 1.4.0"

# 3. tlshd -v (short form) also prints the same version
if ver_short=$("$T" -v 2>&1); then
    check_contains "tlshd -v carries 'ktls-utils 1.4.0'" "$ver_short" "ktls-utils 1.4.0"
else
    fail "tlshd -v did not exit 0"
fi

# 4. tlshd --help exits 0 and prints a usage line
if help=$("$T" --help 2>&1); then
    check_contains "tlshd --help prints 'usage:'" "$help" "usage:"
else
    fail "tlshd --help did not exit 0"
fi

# 5. negative control: an unknown option must be rejected
if "$T" --definitely-not-a-real-option >/dev/null 2>&1; then
    fail "tlshd should reject an unknown option"
else
    pass "tlshd rejects an unknown option"
fi

# 6. negative control: an unreadable explicit config file must be rejected
if "$T" -c /nonexistent/ktls-utils-test-missing.conf >/dev/null 2>&1; then
    fail "tlshd -c <missing> should have failed"
else
    pass "tlshd rejects a nonexistent explicit config"
fi

echo "ASSERTIONS: $ASSERTIONS, FAILURES: $FAILURES"
if [ "$FAILURES" -ne 0 ]; then
    exit 1
fi
exit 0
