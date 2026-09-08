#!/usr/bin/env bash
set -euo pipefail

passed=0
failed=0
discovered=4
workdir="${TMPDIR:-$PWD}/bmk-test-$$"

cleanup() {
    rm -rf "$workdir"
}
trap cleanup EXIT HUP INT TERM
mkdir -p "$workdir"

pass() {
    passed=$((passed + 1))
    printf '[PASS] %s\n' "$1"
}

fail() {
    failed=$((failed + 1))
    printf '[FAIL] %s\n' "$1"
}

help_output=$(mk -h 2>&1) || help_rc=$?
help_rc=${help_rc:-0}
case "$help_output" in
    *"bmk v0.1"*) version_ok=1 ;;
    *) version_ok=0 ;;
esac
if [ "$help_rc" -eq 1 ] && [ "$version_ok" -eq 1 ]; then
    pass "help output reports bmk v0.1"
else
    fail "help output or exit code differs (rc=$help_rc)"
fi

cat > "$workdir/Mkfile" <<'EOF'
GREETING = hello

all: result.txt

input.txt:
	printf '%s\n' world > input.txt

result.txt: input.txt
	printf '%s %s\n' ${GREETING} "$$(cat input.txt)" > result.txt
EOF

if (cd "$workdir" && mk); then
    pass "packaged mk executes a real build graph"
else
    fail "packaged mk failed to execute the build graph"
fi

if [ "$(cat "$workdir/result.txt")" = "hello world" ]; then
    pass "macro expansion and shell command output are correct"
else
    fail "generated output is incorrect"
fi

printf 'sentinel\n' >> "$workdir/result.txt"
if (cd "$workdir" && mk) && grep -q '^sentinel$' "$workdir/result.txt"; then
    pass "up-to-date target is not rebuilt"
else
    fail "up-to-date target was unexpectedly rebuilt"
fi

if [ "$failed" -eq 0 ]; then
    result_passed=true
else
    result_passed=false
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test_bmk.sh","discovered":%d,"passedCount":%d}\n' \
    "$result_passed" "$discovered" "$passed"

[ "$failed" -eq 0 ]
