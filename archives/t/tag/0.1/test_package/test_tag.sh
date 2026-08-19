#!/bin/sh
# Functional checks for the packaged `tag` binary (mafintosh/tag 0.1.0).
# Runs the real binary with real stdin payloads and asserts on stdout/stderr
# plus exit codes. Upstream stamp buffer ends with ' ' and '\0' and main()
# writes stamp_len bytes, so the stream carries NUL bytes between the stamp
# and the line: output is normalized with `tr -d '\000'` before comparison
# (semantics identical to the README examples).
# Emits the HMBS_TEST_PACKAGE_RESULT marker with the real assertion counts.

set -u

passed=0
failed=0
discovered=5

check() {
    desc="$1"
    expected="$2"
    actual="$3"
    if [ "$expected" = "$actual" ]; then
        passed=$((passed + 1))
        echo "[PASS] $desc"
    else
        failed=$((failed + 1))
        echo "[FAIL] $desc"
        echo "  expected: $expected"
        echo "  actual:   $actual"
    fi
}

# 1) message prefix: `printf 'world\n' | tag hello` -> "hello world"
out=$(printf 'world\n' | tag hello | tr -d '\000')
check "message prefix tags stdin line" "hello world" "$out"

# 2) %l line counter: first line stamped 00000, second 00001
exp=$(printf '00000 a\n00001 b')
out=$(printf 'a\nb\n' | tag %l | tr -d '\000')
check "%l line counter increments per line" "$exp" "$out"

# 3) %d date stamp expands to YYYY-MM-DD HH:MM:SS (19 chars) + " x"
out=$(printf 'x\n' | tag %d | tr -d '\000')
ts=${out% x}
case "$ts" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]\ [0-9][0-9]:[0-9][0-9]:[0-9][0-9])
        passed=$((passed + 1))
        echo "[PASS] %d date stamp expands to 19-char timestamp"
        ;;
    *)
        failed=$((failed + 1))
        echo "[FAIL] %d date stamp -> $out"
        ;;
esac

# 4) no arguments -> usage text on stdout, exit code 1
usage=$(tag 2>/dev/null)
rc=$?
case "$usage" in
    *"Usage: tag"*) has_usage=1 ;;
    *) has_usage=0 ;;
esac
if [ "$rc" -eq 1 ] && [ "$has_usage" -eq 1 ]; then
    passed=$((passed + 1))
    echo "[PASS] no args prints usage and exits 1"
else
    failed=$((failed + 1))
    echo "[FAIL] no args: rc=$rc usage_has_usage_line=$has_usage"
fi

# 5) invalid format (%z) -> stderr "invalid format", exit code 2
err=$(printf 'x\n' | tag %z 2>&1 >/dev/null)
rc=$?
if [ "$rc" -eq 2 ] && [ "$err" = "invalid format" ]; then
    passed=$((passed + 1))
    echo "[PASS] invalid format exits 2 with stderr message"
else
    failed=$((failed + 1))
    echo "[FAIL] invalid format: rc=$rc stderr=$err"
fi

# HMBS marker — numbers come from the real counters above.
if [ "$failed" -eq 0 ]; then
    result_passed="true"
else
    result_passed="false"
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test_tag.sh","discovered":%d,"passedCount":%d}\n' \
    "$result_passed" "$discovered" "$passed"

if [ "$failed" -gt 0 ]; then
    exit 1
fi
exit 0
