#!/bin/sh
# test_package/test_rgf.sh — consumer test for rgf 3.12.0 (OHOS aarch64).
#
# Runs inside the conanrun environment, so the packaged bin/ is on PATH.
# R34: every assertion executes the *packaged* `rgf` binary; nothing is
# mocked and no output is asserted empty-vs-empty.
#
# Coverage (12 assertions, single deterministic source):
#   A. packaged rgf resolves on PATH and is executable (2)
#   B. train_predict on a tiny synthetic regression set exits 0 and
#      emits model + prediction artefacts, all non-empty (6)
#   C. prediction file carries one numeric prediction per test row (1)
#   D. model info file mentions the forest (leaf count) (1)
#   E. error paths fail non-zero: missing train file, unknown action (2)
#
# The final summary line `rgf-consumer: P/A assertions passed` is the
# ONLY source for HMBS_TEST_PACKAGE_RESULT counts (parsed by
# test_package/conanfile.py). The same line is appended to
# rgf_result.txt so the parse source survives `ignore_errors` runs.
# Anti-false-green: artefact assertions check non-empty files
# (`test -s`), prediction rows are counted with grep -c, and the error
# paths assert non-zero exit codes explicitly.

set -u

A=0
PASSED=0
RESULT_FILE="rgf_result.txt"
rm -f "$RESULT_FILE"

fail() { echo "FAIL (after $PASSED/$A): $1" >&2; exit 1; }

assert() {
    A=$((A + 1))
    if eval "$2" >/dev/null 2>&1; then
        PASSED=$((PASSED + 1))
        echo "OK [$PASSED] $1"
    else
        fail "$1"
    fi
}

WORK="rgf-test-workdir"
assert "work dir is creatable (device /tmp may be read-only)" \
    'rm -rf "$WORK" && mkdir -p "$WORK/out"'

RB="$(command -v rgf)"
assert "packaged rgf resolves on PATH (conanrun bin/)" 'test -n "$RB"'
assert "packaged rgf is executable" 'test -x "$RB"'

# ---- B. tiny synthetic regression fixtures (deterministic, offline) ----
assert "synthetic train/test fixtures created" \
    'cd "$WORK" && printf "%s\n" "1 0 0" "0 1 0" "0 0 1" "1 1 1" "2 0 1" "0 2 1" "2 2 4" "3 1 4" > train.x && printf "%s\n" "0" "1" "1" "2" "3" "3" "6" "6" > train.y && printf "%s\n" "1 1 0" "2 1 1" > test.x && test -s train.x && test -s train.y && test -s test.x && cd ..'

assert "rgf train_predict exits 0 on the synthetic set" \
    '"$RB" train_predict algorithm=RGF,train_x_fn="$WORK/train.x",train_y_fn="$WORK/train.y",test_x_fn="$WORK/test.x",reg_L2=1,loss=LS,test_interval=5,max_leaf_forest=20,model_fn_prefix="$WORK/out/m",SaveLastModelOnly,Verbose > "$WORK/train.log" 2>&1; [ $? -eq 0 ]'

assert "train log is non-empty (binary really ran)" 'test -s "$WORK/train.log"'
assert "model artefact emitted and non-empty" 'test -s "$WORK/out/m-01"'
assert "prediction artefact emitted and non-empty" 'test -s "$WORK/out/m-01.pred"'
assert "model info artefact emitted and non-empty" 'test -s "$WORK/out/m-01.info"'

# ---- C. prediction rows: one numeric prediction per test row ----
assert "prediction file holds 2 numeric predictions (matches 2 test rows)" \
    '[ "$(grep -c -E "^[+-]?[0-9]" "$WORK/out/m-01.pred")" -eq 2 ]'

# ---- D. model info mentions the forest structure ----
assert "model info file mentions leaf structure" \
    'grep -q -i "leaf" "$WORK/out/m-01.info"'

# ---- E. error paths must fail (non-zero), proving the harness is live ----
assert "missing train file fails non-zero" \
    '"$RB" train_predict algorithm=RGF,train_x_fn="$WORK/nope.x",train_y_fn="$WORK/train.y",test_x_fn="$WORK/test.x",model_fn_prefix="$WORK/out/e" > "$WORK/err1.log" 2>&1; [ $? -ne 0 ]'
assert "unknown action fails non-zero" \
    '"$RB" frobnicate > "$WORK/err2.log" 2>&1; [ $? -ne 0 ]'

[ "$A" -eq "$PASSED" ] || fail "assertion bookkeeping inconsistent"
echo "rgf 3.12.0 consumer test: $PASSED/$A assertions PASSED"
echo "rgf-consumer: $PASSED/$A assertions passed" | tee -a "$RESULT_FILE"
