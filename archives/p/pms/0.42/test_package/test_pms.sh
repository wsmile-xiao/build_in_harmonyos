#!/bin/sh
# test_pms.sh <pms_binary> — consumer functional test for pms 0.42.
#
# pms is an interactive ncurses program, so the harness only exercises its
# non-interactive CLI surface: -v version banner, --help usage text, and the
# unknown-option error path. All checks invoke the real installed binary.
# Note: pms prints -v/--help then exits with PMS_EXIT_BADARGS (4); that is
# upstream behavior, so every invocation is guarded with `|| true`.
BIN="$1"
PASS=0
FAIL=0

ok() {
    PASS=$((PASS + 1))
    echo "PASS: $1"
}
bad() {
    FAIL=$((FAIL + 1))
    echo "FAIL: $1"
}

if [ -z "$BIN" ]; then
    echo "FAIL: no binary path given"
    echo "RESULT: 0 passed, 1 failed"
    exit 1
fi

# 1. binary exists and is executable
if [ -x "$BIN" ]; then
    ok "binary exists and is executable: $BIN"
else
    bad "binary missing or not executable: $BIN"
fi

# 2. `pms -v` prints a version banner containing 0.42
VER_OUT=$("$BIN" -v 2>&1 || true)
if [ -n "$VER_OUT" ] && echo "$VER_OUT" | grep -q "0\.42"; then
    ok "-v banner contains 0.42"
else
    bad "-v banner missing 0.42 (got: $VER_OUT)"
fi

# 3. `pms -v` header names the program (proves real binary, not a stub)
if [ -n "$VER_OUT" ] && echo "$VER_OUT" | grep -q "Practical Music Search"; then
    ok "-v banner names Practical Music Search"
else
    bad "-v banner missing program name (got: $VER_OUT)"
fi

# 4. `pms --help` prints usage text
HELP_OUT=$("$BIN" --help 2>&1 || true)
if [ -n "$HELP_OUT" ] && echo "$HELP_OUT" | grep -q "Usage:"; then
    ok "--help contains Usage:"
else
    bad "--help missing Usage: (got: $HELP_OUT)"
fi

# 5. `--help` documents the MPD connection options (proves full usage path)
if [ -n "$HELP_OUT" ] && echo "$HELP_OUT" | grep -qi "hostname"; then
    ok "--help documents hostname option"
else
    bad "--help missing hostname option (got: $HELP_OUT)"
fi

# 6. unknown option is rejected with an explicit error (proves arg parser)
BAD_OUT=$("$BIN" -Z 2>&1 || true)
if [ -n "$BAD_OUT" ] && echo "$BAD_OUT" | grep -qi "unknown option"; then
    ok "unknown option rejected explicitly"
else
    bad "unknown option not rejected (got: $BAD_OUT)"
fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
