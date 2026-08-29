#!/bin/sh
# Consumer smoke + functional tests for the installed burp2 binaries.
#
# Exit-code contract (verified against the real burp2 CLI on OHOS):
#   - `burp -v` prints the version and exits 0.
#   - `burp -h` / `vss_strip -h` print usage and exit 1 by design (help is
#     treated as a non-run action), so they are asserted on rc + usage text.
#
# Test cases and assertions are kept distinct and counted separately.
# The PATH comes from Conan's run environment (bin + sbin) which reflects
# exactly where package() installs the binaries (sbin/burp, bin/vss_strip).
#
# Temporary files live under the system temp dir (mktemp) and are removed via
# trap on EXIT/INT/TERM; nothing is written into the archive/package dirs.

set +e
PASS=0
FAIL=0
ASSERT=0

# P3: use mktemp for a unique temp file, cleaned up via trap.
OUT_DIR="$(mktemp -d 2>/dev/null)" || { echo "FAIL: cannot create temp dir"; exit 1; }
trap 'rm -rf "$OUT_DIR"' EXIT INT TERM
OUT="$OUT_DIR/burp2test.out"

# run_case <name> <expected_rc> <grep_pattern> <cmd...>
#   - runs the command, records its exit code;
#   - asserts the exit code equals expected_rc;
#   - asserts stdout+stderr matches the grep pattern.
# Both the rc check and the output check are real assertions; a missing
# binary (command not found -> 127), startup failure, or error-only output
# fails the case instead of passing.
run_case() {
    name="$1"; exp_rc="$2"; pattern="$3"; shift 3
    "$@" >"$OUT" 2>&1
    rc=$?
    ASSERT=$((ASSERT + 1))
    if [ "$rc" -eq "$exp_rc" ]; then
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name — expected rc=$exp_rc got rc=$rc"
        FAIL=$((FAIL + 1))
    fi
    ASSERT=$((ASSERT + 1))
    if grep -qiE "$pattern" "$OUT"; then
        PASS=$((PASS + 1))
    else
        echo "FAIL: $name — output does not match '$pattern'"
        FAIL=$((FAIL + 1))
    fi
}

# 1) version — burp -v prints a strict version string and exits 0.
run_case "burp -v (version, rc=0)" 0 "^burp-2\.1\.0" burp -v
# 2) help — burp -h prints usage and exits 1 by design.
run_case "burp -h (usage, rc=1)" 1 "usage" burp -h
# 3) vss_strip -h prints usage and exits 1 by design.
run_case "vss_strip -h (usage, rc=1)" 1 "usage" vss_strip -h

echo "==== BURP2 CONSUMER TEST SUMMARY ===="
echo "cases: $((PASS + FAIL))  assertions: $ASSERT  passed: $PASS  failed: $FAIL"
if [ "$FAIL" -eq 0 ]; then
    echo "RESULT: ALL_PASS"
    exit 0
else
    echo "RESULT: SOME_FAILED"
    exit 1
fi
