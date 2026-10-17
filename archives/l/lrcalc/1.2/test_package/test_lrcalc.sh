#!/bin/sh
# Functional test for the packaged lrcalc/schubmult executables (R34).
# Expected outputs are the upstream README examples; the script fails if the
# binaries are missing or produce different output.
set -u

fail=0

check () {
    name=$1
    expected=$2
    shift 2
    got=$("$@" 2>/dev/null)
    if [ "$got" = "$expected" ]; then
        echo "ok $name"
    else
        echo "FAIL $name"
        echo "--- expected ---"
        printf '%s\n' "$expected"
        echo "--- got ---"
        printf '%s\n' "$got"
        fail=1
    fi
}

check "lrcalc coef 3 2 1 - 2 1 - 2 1" "2" \
    lrcalc coef 3 2 1 - 2 1 - 2 1

check "lrcalc skew 3 2 1 / 2 1" "1  (3)
2  (2, 1)
1  (1, 1, 1)" \
    lrcalc skew 3 2 1 / 2 1

check "lrcalc mult -q 3,2 3 2 1 - 3 2 1" "1  (2)
1  (1, 1)" \
    lrcalc mult -q 3,2 3 2 1 - 3 2 1

check "schubmult 1 3 2 - 1 3 2" "1  (1, 4, 2, 3)
1  (2, 3, 1)" \
    schubmult 1 3 2 - 1 3 2

if [ "$fail" -ne 0 ]; then
    echo "CLI checks FAILED"
    exit 1
fi
echo "CLI_OK: 4 checks passed"
