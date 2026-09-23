#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "[FAIL] usage: run_test.sh TEST_BINARY [ARG ...]" >&2
    exit 2
fi

test_binary="$1"
shift
tmp_root="${TMPDIR:-.}"
stdout_log="${tmp_root}/ruckig-test-$$.stdout"
stderr_log="${tmp_root}/ruckig-test-$$.stderr"
trap 'rm -f "$stdout_log" "$stderr_log"' EXIT

printf -v command_line '%q ' "$test_binary" "$@"
command_line="${command_line% }"
echo "[STEP] 1/1 run Ruckig consumer validation"
echo "[STEP] command: ${command_line}"

set +e
"$test_binary" "$@" >"$stdout_log" 2>"$stderr_log"
exit_code=$?
set -e

echo "[EXIT] code=${exit_code}"
echo "[STDOUT]"
if [ -s "$stdout_log" ]; then
    cat "$stdout_log"
else
    echo "<empty>"
fi

echo "[STDERR]"
if [ -s "$stderr_log" ]; then
    cat "$stderr_log"
else
    echo "<empty>"
fi

if [ "$exit_code" -ne 0 ]; then
    echo "[FAIL] Ruckig consumer validation failed with exit code ${exit_code}" >&2
    exit "$exit_code"
fi

echo "[PASS] Ruckig consumer validation completed"
