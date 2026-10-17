#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer smoke test for the packaged lsof binary.
# Called by conanfile.py test() with LSOF_BIN pointing at the package binary.
# Real assertions: unexpected output or non-zero exit fails the test.
set -uo pipefail

LSOF_BIN="${LSOF_BIN:-lsof}"
fail() { echo "FAIL: $*"; exit 1; }

[ -x "$LSOF_BIN" ] || fail "lsof binary not found or not executable: $LSOF_BIN"
echo "PASS: lsof binary found and executable"

# 1) Version/revision output (no /proc access needed)
out=$("$LSOF_BIN" -v 2>&1)
rc=$?
[ $rc -eq 0 ] || fail "lsof -v exited $rc: $out"
case "$out" in
    *lsof*) echo "PASS: lsof -v reports version info" ;;
    *) fail "lsof -v produced no version output: $out" ;;
esac

# 2) Real /proc scan: list open files of this shell process
out=$("$LSOF_BIN" -p $$ 2>&1)
rc=$?
[ $rc -eq 0 ] || fail "lsof -p $$ exited $rc: $out"
echo "$out" | grep -q "COMMAND" || fail "lsof -p $$ output has no header: $out"
echo "$out" | grep -qw "bash" || fail "lsof -p $$ did not list the bash process: $out"
echo "PASS: lsof -p \$$ listed open files of the current process"

# 3) FD filter works on a live fd (stdin of this shell is an open file)
out=$("$LSOF_BIN" -p $$ -a -d 0 2>&1)
rc=$?
[ $rc -eq 0 ] || fail "lsof -p $$ -a -d 0 exited $rc: $out"
echo "$out" | grep -qE "(0u?|FD)" || fail "lsof did not report fd 0: $out"
echo "PASS: lsof -d 0 filter reported the expected fd"

echo "[test] All lsof consumer tests passed"
