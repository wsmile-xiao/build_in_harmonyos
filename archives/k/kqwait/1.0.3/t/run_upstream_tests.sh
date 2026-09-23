#!/bin/sh
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR/.."

TESTS=0
FAILED=0

do_test() {
    action="$1"
    expected="$2"
    msg="$3"
    shift 3

    rm -f out.txt err.txt

    ./kqwait "$@" >out.txt 2>err.txt &
    pid=$!

    sleep 0.3

    if ! sh -c "$action"; then
        kill -9 "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
        TESTS=$((TESTS + 3))
        FAILED=$((FAILED + 3))
        echo "not ok - should return ($msg) [ACTION FAILED]"
        echo "not ok - produces no output to stderr ($msg) [ACTION FAILED]"
        echo "not ok - $msg [ACTION FAILED]"
        return 0
    fi

    n=0

    while kill -0 "$pid" 2>/dev/null && [ "$n" -lt 50 ]; do
        sleep 0.1
        n=$((n + 1))
    done

    if kill -0 "$pid" 2>/dev/null; then
        kill -9 "$pid" 2>/dev/null || true
        wait "$pid" 2>/dev/null || true
        TESTS=$((TESTS + 3))
        FAILED=$((FAILED + 3))
        echo "not ok - should return ($msg) [TIMEOUT]"
        echo "not ok - produces no output to stderr ($msg) [TIMEOUT]"
        echo "not ok - $msg [TIMEOUT]"
        return 0
    fi

    if wait "$pid"; then
        rc=0
    else
        rc=$?
    fi

    TESTS=$((TESTS + 1))

    if [ "$rc" -eq 0 ]; then
        echo "ok - should return ($msg)"
    else
        echo "not ok - should return ($msg) [rc=$rc]"
        FAILED=$((FAILED + 1))
    fi

    TESTS=$((TESTS + 1))

    if [ ! -s err.txt ]; then
        echo "ok - produces no output to stderr ($msg)"
    else
        echo "not ok - produces no output to stderr ($msg): $(cat err.txt)"
        FAILED=$((FAILED + 1))
    fi

    TESTS=$((TESTS + 1))
    actual=$(cat out.txt)

    if [ "$actual" = "$expected" ]; then
        echo "ok - $msg"
    else
        echo "not ok - $msg: got '$actual' want '$expected'"
        FAILED=$((FAILED + 1))
    fi
}
test_dir="t"
test_file="$test_dir/test.txt"

mkdir -p "$test_dir"

touch "$test_file"
do_test \
    "printf '%s\n' 'hello world' > '$test_file'" \
    "$test_file" \
    "returns filename on write" \
    "$test_file"

touch "$test_file.1"
do_test \
    "printf '%s\n' 'hello world' > '$test_file.1'" \
    "$test_file.1" \
    "returns correct filename when waiting on multiple files" \
    "$test_file" "$test_file.1"

do_test \
    "printf '%s\n' 'hello world' > '$test_file.2'" \
    "+ $test_file.2" \
    "returns correct filename when creating a file in dir" \
    "$test_dir/"

do_test \
    "rm -f '$test_file'" \
    "- $test_file" \
    "returns correct filename when deleting a file in dir" \
    "$test_dir/"

test_dir_2="$test_dir/test_dir"
test_file_2="$test_dir_2/test.file"

touch "$test_file"
mkdir -p "$test_dir_2"

do_test \
    "touch '$test_file_2'" \
    "+ $test_file_2" \
    "returns correct filename when waiting for file and dir" \
    "$test_file" "$test_dir_2/"

rm -rf "$test_dir_2"
rm -f "$test_file" "$test_file.1" "$test_file.2"

echo ""
echo "# tests=$TESTS failed=$FAILED"

if [ "$FAILED" -eq 0 ]; then
    echo "ALL PASS"
    exit 0
fi

echo "FAILURES PRESENT"
exit 1
