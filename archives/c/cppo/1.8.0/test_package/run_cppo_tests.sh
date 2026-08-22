#!/bin/sh
# run_cppo_tests.sh — Run upstream cppo test suite against cppo_main binary
#
# Positive tests:  cppo_main < input.cppo | diff expected.ref
# Negative tests:  cppo_main < input.cppo 2>stderr; diff stderr expected.ref (expect non-zero exit)
#
# Usage: run_cppo_tests.sh <cppo_main_path> <tests_dir>
#
# Outputs HMBS_TEST_PACKAGE_RESULT JSON on stdout.

set -euo pipefail

CPPO_MAIN="$1"
TESTS_DIR="$2"

if [ -z "${CPPO_MAIN:-}" ] || [ -z "${TESTS_DIR:-}" ]; then
    echo "Usage: $0 <cppo_main_path> <tests_dir>" >&2
    exit 1
fi

if [ ! -x "$CPPO_MAIN" ]; then
    echo "ERROR: cppo_main not found or not executable: $CPPO_MAIN" >&2
    exit 1
fi

cd "$TESTS_DIR"

TOTAL=0
PASSED=0
FAILED=0
FAIL_LIST=""
SKIP_LIST=""

# ─── Positive tests ─────────────────────────────────────────────────────────
# Each positive test: cppo_main < input.cppo, diff output against .ref
# Tests that need special flags are handled individually.

run_positive() {
    name="$1"
    shift
    input="${name}.cppo"
    ref="${name}.ref"

    if [ ! -f "$input" ]; then
        echo "SKIP: $name — missing input fixture: $input" >&2
        SKIP_LIST="$SKIP_LIST $name(!input)"
        return 0
    fi
    if [ ! -f "$ref" ]; then
        echo "SKIP: $name — missing reference fixture: $ref" >&2
        SKIP_LIST="$SKIP_LIST $name(!ref)"
        return 0
    fi

    TOTAL=$((TOTAL + 1))
    out_file="${name}.out"

    if "$CPPO_MAIN" "$@" "$input" > "$out_file" 2>/dev/null; then
        if diff -q "$ref" "$out_file" > /dev/null 2>&1; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
            FAIL_LIST="$FAIL_LIST $name(diff)"
            echo "FAIL: $name — output differs from reference" >&2
        fi
    else
        FAILED=$((FAILED + 1))
        FAIL_LIST="$FAIL_LIST $name(rc)"
        echo "FAIL: $name — cppo_main returned error (expected success)" >&2
    fi
    rm -f "$out_file"
}

# ─── Negative tests ─────────────────────────────────────────────────────────
# Each negative test: cppo_main should fail, stderr matches .ref

run_negative() {
    name="$1"
    input="${name}.cppo"
    ref="${name}.ref"

    if [ ! -f "$input" ]; then
        echo "SKIP: $name — missing input fixture: $input" >&2
        SKIP_LIST="$SKIP_LIST $name(!input)"
        return 0
    fi
    if [ ! -f "$ref" ]; then
        echo "SKIP: $name — missing reference fixture: $ref" >&2
        SKIP_LIST="$SKIP_LIST $name(!ref)"
        return 0
    fi

    TOTAL=$((TOTAL + 1))
    err_file="${name}.err"

    # Run cppo_main, expect non-zero exit code
    rc=0
    "$CPPO_MAIN" "$input" > /dev/null 2>"$err_file" || rc=$?

    if [ "$rc" -ne 0 ]; then
        if diff -q "$ref" "$err_file" > /dev/null 2>&1; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
            FAIL_LIST="$FAIL_LIST $name(err_diff)"
            echo "FAIL: $name — error output differs from reference" >&2
        fi
    else
        FAILED=$((FAILED + 1))
        FAIL_LIST="$FAIL_LIST $name(unexpected_ok)"
        echo "FAIL: $name — cppo_main succeeded (expected failure)" >&2
    fi
    rm -f "$err_file"
}

# ─── Run all positive tests ─────────────────────────────────────────────────

# Standard positive tests (plain cppo_main < input)
for t in comments cond def lexical loc paren_arg scope tuple unmatched \
         higher_order_macros capital; do
    run_positive "$t"
done

# test.cppo uses #include, needs incl.cppo and incl2.cppo in cwd (they are)
run_positive test

# include_define_on_last_line.cppo needs define_on_last_line.cppo in cwd
run_positive include_define_on_last_line

# version.cppo needs -V flags
run_positive version -V X:123.05.2-alpha.1+foo-2.1 -V COQ:8.13+beta1 -V OCAML:4.12.0~alpha1

# ext.cppo needs -x rot13 and -x source extensions
# Note: rot13 uses 'tr' which may differ across platforms; source.sh must be in cwd
out_file="ext.out"
if [ -f "ext.cppo" ] && [ -f "ext.ref" ]; then
    TOTAL=$((TOTAL + 1))
    if "$CPPO_MAIN" -x "rot13:tr '[a-z]' '[n-za-m]'" -x "source:sh source.sh '%F' %B %E" ext.cppo > "$out_file" 2>/dev/null; then
        if diff -q ext.ref "$out_file" > /dev/null 2>&1; then
            PASSED=$((PASSED + 1))
        else
            FAILED=$((FAILED + 1))
            FAIL_LIST="$FAIL_LIST ext(diff)"
            echo "FAIL: ext — output differs from reference" >&2
        fi
    else
        FAILED=$((FAILED + 1))
        FAIL_LIST="$FAIL_LIST ext(rc)"
        echo "FAIL: ext — cppo_main returned error" >&2
    fi
else
    echo "SKIP: ext — missing fixture(s)" >&2
    SKIP_LIST="$SKIP_LIST ext(!fixtures)"
fi
rm -f "$out_file"

# ─── Run all negative tests ─────────────────────────────────────────────────

for t in already_defined applied_to_none arity_mismatch arity_mismatch_indirect \
         at_least_one_arg comment_in_formals expects_no_args \
         expect_ident expect_ident_empty undefined shape_mismatch \
         int_expansion_error extraneous_enddef missing_enddef missing_endscope; do
    run_negative "$t"
done

# ─── Results ─────────────────────────────────────────────────────────────────

echo ""
echo "=== cppo test results ==="
echo "Total: $TOTAL  Passed: $PASSED  Failed: $FAILED"
if [ -n "$FAIL_LIST" ]; then
    echo "Failed:$FAIL_LIST"
fi
if [ -n "$SKIP_LIST" ]; then
    echo "Skipped:$SKIP_LIST" >&2
fi

if [ "$FAILED" -eq 0 ]; then
    RESULT="true"
else
    RESULT="false"
fi

# HMBS JSON output
cat << EOF

HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":$RESULT,"command":"run_cppo_tests.sh","discovered":$TOTAL,"passedCount":$PASSED}
EOF

# Exit with failure if any test failed
[ "$FAILED" -eq 0 ]
