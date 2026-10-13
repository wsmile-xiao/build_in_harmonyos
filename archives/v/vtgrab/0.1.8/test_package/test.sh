#!/usr/bin/env bash
# test_package/test.sh — functional tests for vtgrab 0.1.8
#
# vtgrab is a set of console tools (rvc / rvcd / twiglet), so the tests drive the
# installed executables: CLI contract of all three programs, a real RVC 001.000
# protocol handshake against a live rvcd, and an OHOS aarch64 ELF fingerprint
# check.  Nothing here inspects the source tree: every assertion runs the binaries
# that the package installed.
set -euo pipefail

# Interpreter for the protocol / ELF probes; VTGRAB_PYTHON is exported by
# test_package/conanfile.py with the very interpreter that runs Conan.
PYTHON="${VTGRAB_PYTHON:-python3}"

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "[ok] $1"; }
fail() { FAIL=$((FAIL + 1)); echo "[fail] $1"; }

assert_contains() { # <label> <needle> <command...>
    local label="$1" needle="$2"; shift 2
    local out
    # `|| true` is required: assert_contains deliberately runs commands that may
    # exit non-zero.  The exit code is asserted on its own by assert_exit.
    out="$("$@" 2>&1 || true)"
    if printf '%s' "$out" | grep -qF -- "$needle"; then
        pass "$label"
    else
        fail "$label (expected '$needle', got: $(printf '%s' "$out" | tr '\n' '|'))"
    fi
}

assert_exit() { # <label> <expected_rc> <command...>
    local label="$1" expected="$2"; shift 2
    local rc=0
    "$@" >/dev/null 2>&1 || rc=$?
    if [ "$rc" -eq "$expected" ]; then
        pass "$label"
    else
        fail "$label (expected exit $expected, got $rc)"
    fi
}

echo "=== vtgrab: CLI contract ==="

for prog in rvc rvcd twiglet; do
    assert_exit "$prog is installed and executable" 0 command -v "$prog"
done

# --version must report the real package version: VERSION is substituted by
# ./configure from AM_INIT_AUTOMAKE(vtgrab, 0.1.8), so these three assertions
# prove the recipe version really reached the binaries.
assert_contains "rvc --version reports vtgrab 0.1.8" "RVC (vtgrab 0.1.8)" rvc --version
assert_contains "rvcd --version reports vtgrab 0.1.8" "RVCD (vtgrab 0.1.8)" rvcd --version
assert_contains "twiglet --version reports vtgrab 0.1.8" "ncurses-based RVC (vtgrab 0.1.8)" \
    twiglet --version

# --help must succeed and print usage (twiglet also proves its ncurses link
# resolved, since the dynamic loader must map the program before main() runs).
assert_contains "rvc --help prints usage" "Usage: rvc <host>:<port>" rvc --help
assert_contains "rvcd --help prints usage" "Usage: rvcd :<port>" rvcd --help
assert_contains "twiglet --help prints usage" "Usage: nrvc <host>:<port>" twiglet --help

# Argument validation must fail loudly instead of hanging.
assert_contains "rvc without arguments prints usage" "Usage: rvc <host>:<port>" rvc
assert_exit "rvc without arguments exits 1" 1 rvc
assert_contains "rvc rejects a target without host:port" "Usage: rvc <host>:<port>" rvc no-such-tty
assert_exit "rvc rejects a target without host:port (exit 1)" 1 rvc no-such-tty
assert_exit "rvcd rejects a non-port argument" 1 rvcd no-such-tty
assert_exit "twiglet refuses a closed port" 1 twiglet 127.0.0.1:1

echo ""
echo "=== vtgrab: RVC 001.000 protocol handshake against a live rvcd ==="
if "$PYTHON" "$(dirname "$0")/rvc_protocol_test.py" "${VTGRAB_TEST_PORT:-6161}" rvcd; then
    pass "rvcd speaks the RVC 001.000 wire protocol"
else
    fail "rvcd speaks the RVC 001.000 wire protocol"
fi

echo ""
echo "=== vtgrab: OHOS aarch64 artifact fingerprint ==="
if "$PYTHON" "$(dirname "$0")/ohos_binary_check.py"; then
    pass "all three programs are OHOS aarch64 musl executables"
else
    fail "all three programs are OHOS aarch64 musl executables"
fi

echo ""
# 34 leaf assertions in total (15 CLI contract + 10 RVC protocol + 9 ELF
# fingerprint); this counter adds 2 group entries on top of the 15 CLI ones.
echo "=== summary: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
