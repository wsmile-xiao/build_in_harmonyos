#!/bin/sh
set -e
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'
PASSED=0
FAILED=0

run_test() {
    local name=$1
    local cmd=$2
    local expected_nonzero=$3
    echo -n "Testing $name ... "
    set +e
    eval "$cmd" > /dev/null 2>&1
    exit_code=$?
    set -e
    if [ $expected_nonzero -eq 1 ]; then
        if [ $exit_code -ne 0 ]; then
            echo "${GREEN}PASS${NC} (exit $exit_code)"
            PASSED=$((PASSED + 1))
        else
            echo "${RED}FAIL${NC} (expected non-zero, got 0)"
            FAILED=$((FAILED + 1))
        fi
    else
        if [ $exit_code -eq 0 ]; then
            echo "${GREEN}PASS${NC} (exit 0)"
            PASSED=$((PASSED + 1))
        else
            echo "${RED}FAIL${NC} (expected 0, got $exit_code)"
            FAILED=$((FAILED + 1))
        fi
    fi
}

echo "========================================"
echo "Chaos Marmosets HarmonyOS Test"
echo "========================================"
run_test "divide-by-zero" "./divide-by-zero" 0
run_test "seg-fault" "./seg-fault" 1
echo -n "Check executables exist ... "
if [ -x "./divide-by-zero" ] && [ -x "./seg-fault" ]; then
    echo "${GREEN}PASS${NC}"
    PASSED=$((PASSED + 1))
else
    echo "${RED}FAIL${NC}"
    FAILED=$((FAILED + 1))
fi
echo "----------------------------------------"
echo "PASSED=$PASSED, FAILED=$FAILED"
echo "========================================"
echo "Note: leak-memory not tested automatically (run manually if needed)."
[ $FAILED -eq 0 ] && exit 0 || exit 1
