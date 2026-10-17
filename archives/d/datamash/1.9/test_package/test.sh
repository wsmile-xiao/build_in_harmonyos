#!/usr/bin/env bash
set -euo pipefail

DATAMASH="$1"
DECORATE="$2"
CHECKS=0

expect_eq() {
    name="$1"
    expected="$2"
    actual="$3"
    if [ "$actual" != "$expected" ]; then
        printf 'FAIL: %s\nexpected: %s\nactual:   %s\n' \
            "$name" "$expected" "$actual" >&2
        exit 1
    fi
    CHECKS=$((CHECKS + 1))
    printf 'PASS: %s\n' "$name"
}

case "$("$DATAMASH" --version | sed -n '1p')" in
    "datamash (GNU datamash) 1.9") ;;
    *) printf 'FAIL: datamash version\n' >&2; exit 1 ;;
esac
CHECKS=$((CHECKS + 1))
printf 'PASS: datamash version\n'

case "$("$DECORATE" --version | sed -n '1p')" in
    "decorate (GNU datamash) 1.9") ;;
    *) printf 'FAIL: decorate version\n' >&2; exit 1 ;;
esac
CHECKS=$((CHECKS + 1))
printf 'PASS: decorate version\n'

expect_eq "sum" "6" \
    "$(printf '1\n2\n3\n' | "$DATAMASH" sum 1)"
expect_eq "mean" "2" \
    "$(printf '1\n2\n3\n' | "$DATAMASH" mean 1)"
expect_eq "median" "3" \
    "$(printf '9\n1\n3\n' | "$DATAMASH" median 1)"
expect_eq "grouped sum" "$(printf 'A\t3\nB\t5')" \
    "$(printf 'A\t1\nA\t2\nB\t5\n' | "$DATAMASH" -s -g 1 sum 2)"
expect_eq "transpose" "$(printf '1\t3\n2\t4')" \
    "$(printf '1\t2\n3\t4\n' | "$DATAMASH" transpose)"
expect_eq "tabular check" "2 lines, 2 fields" \
    "$(printf '1\t2\n3\t4\n' | "$DATAMASH" check)"
expect_eq "roman sort" "$(printf 'III\nV\nIX\nXI\nC')" \
    "$(printf 'C\nV\nIII\nIX\nXI\n' | "$DECORATE" -k1,1:roman)"

if printf '1\n' | "$DATAMASH" sum 0 >/dev/null 2>&1; then
    printf 'FAIL: invalid field was accepted\n' >&2
    exit 1
fi
CHECKS=$((CHECKS + 1))
printf 'PASS: invalid field rejected\n'

if [ "$CHECKS" -ne 10 ]; then
    printf 'FAIL: expected 10 checks, ran %s\n' "$CHECKS" >&2
    exit 1
fi
printf 'All %s packaged-command checks passed.\n' "$CHECKS"
