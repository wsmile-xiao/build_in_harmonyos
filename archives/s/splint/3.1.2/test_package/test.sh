#!/bin/sh
# Consumer verification for splint 3.1.2 — HarmonyOS PC (OHOS / aarch64).
#
# Invoked by test_package/conanfile.py as
#     TMPDIR=<writable> bash test.sh <path-to-installed-splint>
# LARCH_PATH comes from the package's runenv_info (VirtualRunEnv); TMPDIR from the
# test_package recipe.  Every check calls the packaged tool and asserts on its real
# output / exit status — there is no stub.

set -u

SPLINT="${1:-splint}"
HERE="$(cd "$(dirname "$0")" && pwd)"
CHECKS=0

fail() {
    echo "FAIL: $1"
    exit 1
}

pass() {
    CHECKS=$((CHECKS + 1))
    echo "PASS $CHECKS: $1"
}

run_splint() {
    # usage: run_splint <args...>;  sets $OUT and $RC
    OUT=$("$SPLINT" "$@" 2>&1)
    RC=$?
}

echo "--- splint 3.1.2 consumer verification ---"

# 1. the tool starts, identifies itself and accepts -help
run_splint -help
[ "$RC" -eq 0 ] || fail "-help exited $RC"
echo "$OUT" | grep -q "Splint 3.1.2" || fail "-help banner lacks 'Splint 3.1.2'"
pass "-help exits 0 and reports 'Splint 3.1.2'"

# 2. the model library declared through runenv_info is really installed
[ -n "${LARCH_PATH:-}" ] || fail "LARCH_PATH not published by the package"
larch_first=${LARCH_PATH%%:*}
[ -f "$larch_first/standard.lcd" ] || fail "no standard.lcd in $larch_first"
pass "LARCH_PATH=$larch_first contains standard.lcd"

# 3. a clean translation unit is accepted without warnings (exit 0)
run_splint "$HERE/clean.c"
[ "$RC" -eq 0 ] || fail "clean.c exited $RC: $OUT"
echo "$OUT" | grep -q "no warnings" || fail "clean.c: unexpected output [$OUT]"
pass "clean.c analysed with no warnings (exit 0)"

# 4. a defective translation unit is reported (exit 1) with the expected diagnostics
run_splint "$HERE/warn.c"
[ "$RC" -eq 1 ] || fail "warn.c exited $RC, expected 1"
echo "$OUT" | grep -q "Variable uninit_value used before definition" ||
    fail "warn.c: missing use-before-definition diagnostic [$OUT]"
echo "$OUT" | grep -q "Variable unused_value declared but not used" ||
    fail "warn.c: missing unused-variable diagnostic [$OUT]"
echo "$OUT" | grep -q "Finished checking --- 2 code warnings" ||
    fail "warn.c: unexpected summary [$OUT]"
pass "warn.c reports both expected diagnostics (exit 1)"

# 5. a translation unit that #includes a local header exercises the pre-processor
#    scratch path (TMPDIR), i.e. the read-only-/tmp workaround actually works
run_splint "$HERE/withinclude.c"
[ "$RC" -eq 0 ] || fail "withinclude.c exited $RC: $OUT"
echo "$OUT" | grep -q "no warnings" || fail "withinclude.c: unexpected output [$OUT]"
pass "withinclude.c pre-processed through TMPDIR and analysed (exit 0)"

echo "test splint 3.1.2: $CHECKS/$CHECKS checks PASS"
exit 0
