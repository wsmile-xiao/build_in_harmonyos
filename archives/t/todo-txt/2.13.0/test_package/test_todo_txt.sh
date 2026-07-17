#!/usr/bin/env bash
# test_package/test_todo_txt.sh — smoke test for todo-txt CLI
set -euo pipefail

TODO_CMD=${TODOTXT_TEST_CMD:-todo.sh}
CONFIG_FILE=${TODOTXT_TEST_CONFIG:?TODOTXT_TEST_CONFIG is required}
WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/todo-txt-test.XXXXXX")
trap 'rm -rf "$WORK_DIR"' EXIT

cat > "$WORK_DIR/config" <<EOF_CFG
export TODO_DIR="$WORK_DIR"
export TODO_FILE="\$TODO_DIR/todo.txt"
export DONE_FILE="\$TODO_DIR/done.txt"
export REPORT_FILE="\$TODO_DIR/report.txt"
export TODOTXT_VERBOSE=1
export TODOTXT_PLAIN=1
EOF_CFG

: > "$WORK_DIR/todo.txt"
: > "$WORK_DIR/done.txt"

VERSION_OUTPUT=$("$TODO_CMD" -d "$CONFIG_FILE" -V 2>&1 || true)
printf '%s\n' "$VERSION_OUTPUT" | grep -F "v2.13.0"
"$TODO_CMD" -d "$WORK_DIR/config" add "write conan recipe +ohos @build"
"$TODO_CMD" -d "$WORK_DIR/config" list | grep -F "write conan recipe +ohos @build"
"$TODO_CMD" -d "$WORK_DIR/config" do 1
"$TODO_CMD" -d "$WORK_DIR/config" archive

grep -F "x " "$WORK_DIR/done.txt" | grep -F "write conan recipe +ohos @build"
if grep -F "write conan recipe" "$WORK_DIR/todo.txt" >/dev/null 2>&1; then
    echo "todo.txt should be empty after archive" >&2
    exit 1
fi

# Confirm the packaged global config is readable by the CLI too.
"$TODO_CMD" -d "$CONFIG_FILE" shorthelp >/dev/null

echo "todo-txt smoke test: PASS"
