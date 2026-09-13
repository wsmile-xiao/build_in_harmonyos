#!/bin/sh
set -eu

bin=${1:?usage: test.sh /path/to/cek}
passed=0
failed=0

check_contains() {
    name=$1
    expected=$2
    shift 2
    output=$("$@" 2>&1 || true)
    case "$output" in
        *"$expected"*)
            passed=$((passed + 1))
            printf 'PASS: %s\n' "$name"
            ;;
        *)
            failed=$((failed + 1))
            printf 'FAIL: %s (missing %s)\n' "$name" "$expected" >&2
            ;;
    esac
}

check_contains "cek --version" "0.2.0" "$bin" --version
check_contains "cek version" "cek version 0.2.0" "$bin" version
check_contains "cek version with path" "cek version 0.2.0" "$bin" version .
check_contains "cek help" "Usage: cek" "$bin" --help

if "$bin" version one two >/dev/null 2>&1; then
    failed=$((failed + 1))
    printf 'FAIL: invalid argument count unexpectedly succeeded\n' >&2
else
    passed=$((passed + 1))
    printf 'PASS: invalid argument count\n'
fi

if [ -f "$bin" ]; then
    passed=$((passed + 1))
    printf 'PASS: installed binary path\n'
else
    failed=$((failed + 1))
    printf 'FAIL: installed binary path\n' >&2
fi

printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"failed":%s,"discovered":6,"passedCount":%s}\n' \
    "$passed" "$failed" "$passed"

[ "$failed" -eq 0 ]
