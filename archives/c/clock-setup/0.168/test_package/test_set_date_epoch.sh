#!/bin/sh
# test_package/test_set_date_epoch.sh — clock-setup 0.168 consumer test.
#
# Really executes the packaged bin/set-date-epoch binary (R34: no stub).
# The program is silent and exits 0 when the system clock is sane
# (post-1970); it only prints/corrects when the date predates the epoch.
#
# Falsifiability: an `exit 0` stub fails cases 2-3 (no program strings);
# a stub printing "test passed" fails case 5 (stdout must be empty).
#
# Output: one [PASS]/[FAIL] line per case, final line always
#   RESULT: <N> passed, <M> failed
# parsed by test_package/conanfile.py into HMBS_TEST_PACKAGE_RESULT.

BIN="${SET_DATE_EPOCH_BIN:-set-date-epoch}"
BASE="${TMPDIR:-/tmp}/clock-setup-test-$$"

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

# ---- case 1: binary exists and is executable -----------------------------
if [ -x "$BIN" ]; then
    ok "binary exists and is executable ($BIN)"
else
    ko "binary missing or not executable ($BIN)"
fi

# ---- cases 2-3: real program strings present (anti-stub) ------------------
# NOTE (CI #42914/#42942): `grep -q` then `grep -a -q` both reported the
# strings as missing on CI workers while the binary executes fine, so the
# string probe must not depend on the worker's grep (toybox grep skips
# binaries; curl/grep-class tools are even absent from the worker PATH).
# Use a python3 byte search first (binary-safe, NUL-safe), fall back to
# grep -a only when no python3 is usable. Counts and RESULT format unchanged.
bin_contains() {
    _needle="$1"
    for _py in "${HMBS_PYTHON3:-}" python3 /data/app/bin/python3 /data/service/hnp/bin/python3; do
        [ -n "$_py" ] || continue
        if command -v "$_py" >/dev/null 2>&1; then
            if "$_py" -c 'import sys; data=open(sys.argv[1],"rb").read(); sys.exit(0 if sys.argv[2].encode() in data else 1)' "$BIN" "$_needle" >/dev/null 2>&1; then
                return 0
            else
                return 1
            fi
        elif [ -x "$_py" ]; then
            if "$_py" -c 'import sys; data=open(sys.argv[1],"rb").read(); sys.exit(0 if sys.argv[2].encode() in data else 1)' "$BIN" "$_needle" >/dev/null 2>&1; then
                return 0
            else
                return 1
            fi
        fi
    done
    grep -a -q "$_needle" "$BIN" >/dev/null 2>&1
}

if bin_contains "System date is before"; then
    ok "binary embeds pre-epoch correction message"
else
    ko "correction message string not found in binary"
fi

if bin_contains "1-1-1970"; then
    ok "binary embeds epoch reference string"
else
    ko "epoch reference string not found in binary"
fi

# ---- cases 4-6: execute on a sane clock ----------------------------------
"$BIN" > "$BASE/stdout.log" 2> "$BASE/stderr.log"
rc=$?

if [ "$rc" -eq 0 ]; then
    ok "exit code 0 on sane system clock (rc=$rc)"
else
    ko "unexpected exit code (rc=$rc)"
fi

if [ ! -s "$BASE/stdout.log" ]; then
    ok "stdout empty (no pre-epoch correction attempted)"
else
    ko "unexpected stdout content"
    sed 's/^/       | /' "$BASE/stdout.log"
fi

if [ ! -s "$BASE/stderr.log" ]; then
    ok "stderr empty (no error reported)"
else
    ko "unexpected stderr content"
    sed 's/^/       | /' "$BASE/stderr.log"
fi

say "RESULT: $passed passed, $failed failed"
finish
