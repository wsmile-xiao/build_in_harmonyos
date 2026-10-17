#!/bin/sh
# test_package consumer test for eta 1.0.1.
# Every functional run completes on the first progress sample, so no test
# sleeps: upstream rejects -i 0, and sleep only happens after the completion
# break. 16 deterministic checks against the installed binary.
export PATH="$PATH:/system/bin"

checks=0
fail() { echo "FAIL: $1"; exit 1; }
ok() { checks=$((checks+1)); echo "PASS $checks: $1"; }

echo "--- eta 1.0.1 consumer verification ---"

# 1. --help
out=$(eta --help) || fail "--help exited non-zero"
ok "--help exits 0"
echo "$out" | grep -q "Usage:" || fail "--help output missing Usage:"
ok "--help prints Usage:"

# 2. functional: target 5, command reports 10 -> completes on first sample
out=$(eta 5 echo 10) || fail "functional run exited non-zero"
ok "eta 5 echo 10 exits 0"
echo "$out" | grep -q "100%" || fail "progress output missing 100%"
ok "progress prints 100%"
echo "$out" | grep -q "Done" || fail "progress output missing Done"
ok "progress prints Done"

# 3. --width option
out=$(eta -w 20 5 echo 10) || fail "-w run exited non-zero"
ok "eta -w 20 ... exits 0"
echo "$out" | grep -q "100%" || fail "-w output missing 100%"
ok "-w output reaches 100%"

# 4. down counting with explicit --start
out=$(eta -d -s 0 1 echo 1) || fail "down mode exited non-zero"
ok "eta -d -s 0 ... exits 0"
echo "$out" | grep -q "Done" || fail "down mode output missing Done"
ok "down mode prints Done"

# 5. --interval accepted (completion happens before the first sleep)
out=$(eta -i 1 5 echo 10) || fail "-i 1 run exited non-zero"
ok "eta -i 1 ... exits 0"

# 6. --interval 0 rejected by option validation
out=$(eta -i 0 5 echo 10 2>&1); rc=$?
[ "$rc" = "1" ] || fail "invalid -i 0 expected exit 1, got $rc"
ok "eta -i 0 exits 1"
echo "$out" | grep -q "invalid interval argument" || fail "missing invalid-interval message"
ok "invalid interval message printed"

# 7. command without numeric output -> COULD_NOT_PARSE_COMMAND_OUTPUT (3)
out=$(eta 5 true 2>&1); rc=$?
[ "$rc" = "3" ] || fail "no-number command expected exit 3, got $rc"
ok "no-number command output exits 3"
echo "$out" | grep -q "Could not find number" || fail "missing parse-error message"
ok "parse-error message printed"

# 8. no arguments -> INVALID_COMMAND_LINE_ARGUMENTS (1)
out=$(eta 2>&1); rc=$?
[ "$rc" = "1" ] || fail "no-args expected exit 1, got $rc"
ok "no-args exits 1"
echo "$out" | grep -q "no target argument" || fail "missing no-target message"
ok "no-target message printed"

echo "test eta 1.0.1: $checks/16 checks PASS"
[ "$checks" = "16" ] || fail "expected 16 passing checks, got $checks"
exit 0
