#!/bin/sh
# test_package/test.sh — consumer smoke test for the packaged codex-probe binary.
#
# codex-probe is a Go CLI, not a linkable library, so the consumer test exercises
# the installed executable. All six cases are fully offline and are asserted on
# the real diagnostics emitted by upstream main.go at tag v1.0.3:
#
#   1. `--help`                    -> rc 0, prints the Usage block
#   2. (no arguments)              -> rc 0, prints the Usage block
#   3. `--sync --status`           -> rc 1, mutually exclusive commands rejected
#   4. `--config <missing> --login`-> rc 1, config load fails closed
#   5. `--config <file> --login`   -> rc 1, --login without -o fails closed
#   6. `--status --output *.txt`   -> rc 1, --output must be a .csv path
#
# Cases 3-6 all fail BEFORE the upstream network-region probe
# (checkNotChina -> ipinfo.io/api.country.is/ip-api.com), so the test needs no
# network and does not depend on which region the CI worker runs in.
set -u

# HMBS injects TMPDIR/TMP/TEMP; cd there so the shell is not left in an HMDFS cwd
# that breaks getcwd (`[shell_getcwd]` diagnostic).
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-codex-probe>" >&2
    exit 2
fi

probe="$1"
if [ ! -f "$probe" ]; then
    echo "[fail] codex-probe binary not found: $probe" >&2
    exit 1
fi
case "$probe" in
    /*) ;;
    *) probe="$(pwd)/$probe" ;;
esac

PASS=0
FAIL=0
CASES=0

ok()   { PASS=$((PASS + 1)); echo "        [ok] $1"; }
bad()  { FAIL=$((FAIL + 1)); echo "        [fail] $1"; }
check() {
    # check <description> <condition-rc> -> assert condition true
    if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1"; fi
}

assert_rc_zero()     { check "$2" "$([ "$1" -eq 0 ] && echo 0 || echo 1)"; }
assert_rc_nonzero()  { check "$2" "$([ "$1" -ne 0 ] && echo 0 || echo 1)"; }
assert_contains() {
    # assert_contains <haystack-file> <needle> <description>
    # -e is required: several needles start with "--" and would otherwise be
    # parsed by grep as an option (observed as "unrecognized option").
    if grep -Fq -e "$2" "$1"; then ok "$3"; else bad "$3"; fi
}

workdir="$(pwd)/codex-probe-test-$$"
rm -rf "$workdir"
mkdir -p "$workdir"

# ── case 1: --help ────────────────────────────────────────────────────
CASES=$((CASES + 1))
echo "[case 1] codex-probe --help"
out="$workdir/case1.out"
"$probe" --help >"$out" 2>&1
assert_rc_zero $? "--help exits 0"
assert_contains "$out" "Usage:" "--help prints the Usage block"
assert_contains "$out" "--login" "--help documents --login"

# ── case 2: no arguments ──────────────────────────────────────────────
CASES=$((CASES + 1))
echo "[case 2] codex-probe (no arguments)"
out="$workdir/case2.out"
"$probe" >"$out" 2>&1
assert_rc_zero $? "bare invocation exits 0"
assert_contains "$out" "Usage:" "bare invocation prints the Usage block"

# ── case 3: mutually exclusive commands ───────────────────────────────
CASES=$((CASES + 1))
echo "[case 3] codex-probe --sync --status"
out="$workdir/case3.out"
"$probe" --sync --status >"$out" 2>&1
assert_rc_nonzero $? "--sync with --status exits non-zero"
assert_contains "$out" "--sync cannot be combined" \
    "reports the mutually-exclusive command diagnostic"

# ── case 4: missing config file ───────────────────────────────────────
CASES=$((CASES + 1))
echo "[case 4] codex-probe --config <missing> --login"
out="$workdir/case4.out"
"$probe" --config "$workdir/does-not-exist.json" --login >"$out" 2>&1
assert_rc_nonzero $? "missing explicit config exits non-zero"
assert_contains "$out" "failed to load config" "reports the config load failure"

# ── case 5: --login without -o ────────────────────────────────────────
CASES=$((CASES + 1))
echo "[case 5] codex-probe --config <valid> --login"
printf '{}\n' >"$workdir/config.json"
out="$workdir/case5.out"
"$probe" --config "$workdir/config.json" --login >"$out" 2>&1
assert_rc_nonzero $? "--login without -o exits non-zero"
assert_contains "$out" "--login requires -o" "reports the missing -o diagnostic"

# ── case 6: --output must be .csv ─────────────────────────────────────
CASES=$((CASES + 1))
echo "[case 6] codex-probe --status --output report.txt"
out="$workdir/case6.out"
"$probe" --config "$workdir/config.json" --status \
    --output "$workdir/report.txt" "$workdir/config.json" >"$out" 2>&1
assert_rc_nonzero $? "non-csv --output exits non-zero"
assert_contains "$out" "--output path must end with .csv" \
    "reports the non-csv --output diagnostic"

rm -rf "$workdir"

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"/bin/sh test.sh <bin/codex-probe>\",\"discovered\":$CASES,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL assertion(s) failed, $PASS passed, $CASES case(s)"
    exit 1
fi
echo "[ok] all $PASS assertions passed across $CASES cases"
