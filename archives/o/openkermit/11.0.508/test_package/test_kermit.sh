#!/data/service/hnp/bin/bash
# test_kermit.sh — openkermit 11.0.508 consumer test (HarmonyOS PC).
#
# Really executes the packaged `kermit` binary (R34: the binary IS the API).
# Checks 1-3 are CLI contract checks; checks 4-7 re-run the three upstream
# scripting tests (tests/scripts/*.ksc) exactly as upstream's own pytest
# driver tests/test_scripting.py does, so the consumer test carries real
# upstream test cases into the OHOS environment.
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KSC="$SCRIPT_DIR/scripts"
BIN=kermit

discovered=0
passed=0
failed=0

ok()  { discovered=$((discovered + 1)); passed=$((passed + 1)); echo "[OK]   $1"; }
no()  { discovered=$((discovered + 1)); failed=$((failed + 1)); echo "[FAIL] $1"; }
head_line() { echo; echo "=== $1 ==="; }

# --------------------------------------------------------------------------
head_line "check 1/7: $BIN present and executable"
if command -v "$BIN" >/dev/null 2>&1; then
    BINPATH="$(command -v "$BIN")"
    ok "$BIN found on PATH: $BINPATH"
    [ -x "$BINPATH" ] && ok "$BINPATH is executable" \
                      || no "$BINPATH is not executable"
else
    no "$BIN not on PATH (conanrun VirtualRunEnv)"
    BINPATH=""
fi

# --------------------------------------------------------------------------
head_line "check 2/7: --version contract"
# C-Kermit >= 10.0: "--version" prints major.minor only (see ckcmai.c header
# comment); the edit number is exposed by \v(fullversion) instead.
VOUT="$("$BIN" --version </dev/null 2>&1)"
VRC=$?
echo "rc=$VRC output: $(echo "$VOUT" | head -n 3 | tr '\n' '|')"
[ "$VRC" -eq 0 ] && ok "--version exits 0" || no "--version rc=$VRC"
echo "$VOUT" | grep -q "11\.0" && ok "--version contains 11.0" \
                                || no "--version missing 11.0"

# --------------------------------------------------------------------------
head_line "check 3/7: startup herald / \\v(fullversion) carries the edit number"
FOUT="$(printf 'set command more-prompting off\necho \\v(fullversion)\nexit 0\n' \
    | "$BIN" -Y 2>&1)"
FRC=$?
echo "rc=$FRC output: $(echo "$FOUT" | head -n 2 | tr '\n' '|')"
[ "$FRC" -eq 0 ] && ok "inline script exits 0" || no "inline script rc=$FRC"
echo "$FOUT" | grep -q "11\.0\.508" && ok "fullversion contains 11.0.508" \
                                    || no "fullversion missing 11.0.508"
echo "$FOUT" | grep -q "C-Kermit" && ok "fullversion identifies C-Kermit" \
                                  || no "fullversion missing C-Kermit"

# --------------------------------------------------------------------------
# Upstream tests/scripts/*.ksc — driven by upstream tests/test_scripting.py
# (`run_wermit([str(script("...ksc")), "-Y"])`).  Our binary ships as
# `kermit`, upstream's is `wermit`; arguments are otherwise unchanged.
head_line "check 4/7: upstream test_basic.ksc (keywords / macros / dot assign)"
BOUT="$("$BIN" "$KSC/test_basic.ksc" -Y </dev/null 2>&1)"
BRC=$?
echo "rc=$BRC"
echo "$BOUT" | grep -q "TEST_BASIC: Macro value is 42" \
    && ok "test_basic: macro value 42" || no "test_basic: macro value 42 missing"
echo "$BOUT" | grep -q "TEST_BASIC: Variable value is 100" \
    && ok "test_basic: variable value 100" || no "test_basic: variable value 100 missing"
echo "$BOUT" | grep -q "TEST_BASIC: Dot value is 200" \
    && ok "test_basic: dot value 200" || no "test_basic: dot value 200 missing"
[ "$BRC" -eq 0 ] && ok "test_basic exits 0" || no "test_basic rc=$BRC"

head_line "check 5/7: upstream test_args.ksc -- arguments mapped (rc=0)"
AOUT="$("$BIN" "$KSC/test_args.ksc" -Y = hello world </dev/null 2>&1)"
ARC=$?
echo "rc=$ARC output: $(echo "$AOUT" | head -n 2 | tr '\n' '|')"
[ "$ARC" -eq 0 ] && ok "test_args (with args) exits 0" \
                 || no "test_args (with args) rc=$ARC"
echo "$AOUT" | grep -q "TEST_ARGS: Arg 1 is hello" \
    && ok "test_args: arg 1 mapped" || no "test_args: arg 1 not mapped"
echo "$AOUT" | grep -q "TEST_ARGS: Arg 2 is world" \
    && ok "test_args: arg 2 mapped" || no "test_args: arg 2 not mapped"

head_line "check 6/7: upstream test_args.ksc -- missing args must fail (rc!=0)"
FOUT2="$("$BIN" "$KSC/test_args.ksc" -Y </dev/null 2>&1)"
FRC2=$?
echo "rc=$FRC2"
[ "$FRC2" -ne 0 ] && ok "test_args (no args) exits non-zero (rc=$FRC2)" \
                  || no "test_args (no args) unexpectedly rc=0"
echo "$FOUT2" | grep -q "TEST_ARGS_FAIL" \
    && ok "test_args: failure branch reported" || no "test_args: TEST_ARGS_FAIL missing"

head_line "check 7/7: upstream test_control.ksc (conditionals / loops / goto)"
COUT="$("$BIN" "$KSC/test_control.ksc" -Y </dev/null 2>&1)"
CRC=$?
echo "rc=$CRC"
[ "$CRC" -eq 0 ] && ok "test_control exits 0" || no "test_control rc=$CRC"
for m in "SUCCESS verified" "FAILURE verified" "EXIST verified" \
         "COMPARISON verified" "GOTO verified"; do
    echo "$COUT" | grep -q "TEST_CONTROL: $m" \
        && ok "test_control: $m" || no "test_control: $m missing"
done
for i in 1 2 3; do
    for kind in FOR WHILE GOTO; do
        echo "$COUT" | grep -q "TEST_CONTROL: $kind loop $i" \
            && ok "test_control: $kind loop $i" || no "test_control: $kind loop $i missing"
    done
done
for i in 0 4; do
    for kind in FOR WHILE GOTO; do
        echo "$COUT" | grep -q "TEST_CONTROL: $kind loop $i" \
            && no "test_control: $kind loop $i must not appear" \
            || ok "test_control: $kind loop $i absent (bound respected)"
    done
done

# --------------------------------------------------------------------------
echo
echo "-------------------------------------------------------------------"
echo "checks: $passed/$discovered assertions passed, $failed failed"
if [ "$failed" -ne 0 ]; then
    printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"test_kermit.sh","discovered":%d,"passedCount":%d}\n' \
        "$discovered" "$passed"
    exit 1
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,"command":"test_kermit.sh","discovered":%d,"passedCount":%d}\n' \
    "$discovered" "$passed"
# Upstream suite (2026-09-19 rework: dependencies completed, suite really run;
#   see learninglog/20260912openkermit-11.0.508/remod-20260919/ and the PR body):
#   pytest parametrizes the 300 `def test_` into 1792 cases; libcheck has 132
#   tcases (120 runtime assertions).
#   Real run: pytest 1137 passed / 1 failed / 645 skipped / 9 xfailed;
#             libcheck 111/120 assertions passed
#             => 1258 executed, 1248 passed (99.2%).
#   test_package itself only carries the 4 upstream .ksc cases (no pty/network/python).
printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"complete","framework":"pytest+libcheck","scope":"test_package subset (upstream .ksc cases)","command":"kermit tests/scripts/*.ksc -Y (upstream tests/test_scripting.py)","discovered":4,"executed":4,"passed":4,"failed":0,"skipped":0,"upstream_suite":"pytest parametrized 1792 cases + libcheck 132 tcases (120 assertions)","upstream_suite_result":"pytest 1137 passed / 1 failed / 645 skipped / 9 xfailed; libcheck 111/120 assertions passed; total executed 1258, passed 1248 (99.2%)","evidence":"learninglog/20260912openkermit-11.0.508/remod-20260919/","reason":"test_package carries only the 4 upstream .ksc cases (4/4 passing). The full upstream suite was really executed in this adaptation environment (OHOS aarch64) after completing the missing dependencies per the official rule (registry check/0.15.2 + pip pytest stack); per-class attribution of skips/failures is in the PR body."}\n'
exit 0
