#!/bin/sh
# test_package/test_cputool.sh — cputool 1.1.0 consumer functional test
#
# Really executes the tested package's bin/cputool binary (R34 anti-hollow),
# under $TMPDIR with 5 content-level functional checks. POSIX sh only,
# toybox-compatible commands.
# Output: one [PASS]/[FAIL] line per case, last line fixed as
#   RESULT: <N> passed, <M> failed
# Parsed by test_package/conanfile.py into HMBS_TEST_PACKAGE_RESULT.
# Falsification design: every content assertion requires non-empty output
# with the expected keyword (grep on empty files fails); error-path cases
# require nonzero exit, so an exit-0 stub binary cannot pass.

BIN="${CPUTOOL_BIN:-cputool}"
BASE="${TMPDIR:-/tmp}/ct-test-$$"

passed=0
failed=0

say() {
    printf '%s\n' "$*"
}

ok() {
    passed=$((passed + 1))
    say "[PASS] $1"
}

ko() {
    failed=$((failed + 1))
    say "[FAIL] $1"
    if [ -f "$BASE/last_log" ]; then
        sed 's/^/       | /' "$BASE/last_log"
    fi
}

finish() {
    trap - 0
    rm -rf "$BASE" 2>/dev/null
    if [ "$failed" -eq 0 ] && [ "$passed" -gt 0 ]; then
        exit 0
    fi
    exit 1
}
trap finish 0

rm -rf "$BASE"
mkdir -p "$BASE"

# ---- case 1: binary exists and is executable ------------------------------
if [ -f "$BIN" ] && [ -x "$BIN" ]; then
    ok "cputool binary exists and is executable ($BIN)"
else
    ko "cputool binary missing or not executable ($BIN)"
fi

# ---- case 2: -V reports the exact version ---------------------------------
"$BIN" -V > "$BASE/v.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$BASE/v.out" ] && grep -q "cputool 1.1.0" "$BASE/v.out"; then
    ok "-V reports 'cputool 1.1.0'"
else
    ko "-V output missing 'cputool 1.1.0' (rc=$rc)"
fi
cp "$BASE/v.out" "$BASE/last_log" 2>/dev/null

# ---- case 3: --help prints usage ------------------------------------------
"$BIN" --help > "$BASE/h.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$BASE/h.out" ] && grep -q "Usage:" "$BASE/h.out"; then
    ok "--help prints usage"
else
    ko "--help missing 'Usage:' (rc=$rc)"
fi
cp "$BASE/h.out" "$BASE/last_log" 2>/dev/null

# ---- case 4: no target fails with 'Nothing to manage' ---------------------
"$BIN" > "$BASE/n.out" 2>&1
rc=$?
if [ "$rc" -ne 0 ] && grep -q "Nothing to manage" "$BASE/n.out"; then
    ok "bare run fails with 'Nothing to manage' (rc=$rc)"
else
    ko "bare run should fail with 'Nothing to manage' (rc=$rc)"
fi
cp "$BASE/n.out" "$BASE/last_log" 2>/dev/null

# ---- case 5: invalid cpu limit is rejected ---------------------------------
"$BIN" -c 0 > "$BASE/c.out" 2>&1
rc=$?
if [ "$rc" -ne 0 ] && grep -q "must be in above 1" "$BASE/c.out"; then
    ok "-c 0 rejected with range error (rc=$rc)"
else
    ko "-c 0 should be rejected with range error (rc=$rc)"
fi
cp "$BASE/c.out" "$BASE/last_log" 2>/dev/null

total=$((passed + failed))
say "RESULT: $passed passed, $failed failed"
finish
