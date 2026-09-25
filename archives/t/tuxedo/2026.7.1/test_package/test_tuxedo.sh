#!/usr/bin/env bash
# tuxedo 2026.7.1 — consumer smoke test（实质调用被测二进制）
# 覆盖 : --version / --help / todo.txt CLI add-list-done 闭环。
set -euo pipefail

TUXEDO="${1:?usage: test_tuxedo.sh /path/to/tuxedo}"
TMP="${TMPDIR:-${HOME:-.}/tmp}"
WORKDIR="$TMP/tuxedo-test-package-$$"
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"' EXIT

PASS=0
TOTAL=7

fail_run() {
    printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"discovered\":${TOTAL},\"passedCount\":${PASS},\"msg\":\"$1\"}"
    exit 1
}

# 1) --version 输出含版本号
V=$("$TUXEDO" --version 2>&1) || fail_run "version"
printf '%s\n' "$V" | grep -F "2026.7.1" >/dev/null || fail_run "version-string"
PASS=$((PASS + 1))

# 2) --help 输出 usage
H=$("$TUXEDO" --help 2>&1) || fail_run "help"
printf '%s\n' "$H" | grep -iE "usage|todo" >/dev/null || fail_run "help-text"
PASS=$((PASS + 1))

export TODO_FILE="$WORKDIR/todo.txt"
export DONE_FILE="$WORKDIR/done.txt"

# 3) add 两条
"$TUXEDO" add "Buy milk due:2026-10-01" >/dev/null 2>&1 || fail_run "add1"
"$TUXEDO" add "Call Bob +family" >/dev/null 2>&1 || fail_run "add2"
PASS=$((PASS + 1))

# 4) list 能列出两条
L=$("$TUXEDO" list 2>&1) || fail_run "list"
printf '%s\n' "$L" | grep -F "Buy milk" >/dev/null || fail_run "list-milk"
printf '%s\n' "$L" | grep -F "Call Bob" >/dev/null || fail_run "list-bob"
PASS=$((PASS + 1))

# 5) listpri / 项目过滤
LP=$("$TUXEDO" listproj 2>&1) || fail_run "listproj"
printf '%s\n' "$LP" | grep -F "+family" >/dev/null || fail_run "listproj-family"
PASS=$((PASS + 1))

# 6) done 1 添加完成前缀（todo.txt 语义：list 仍显示，listall 中标 x）
"$TUXEDO" done 1 >/dev/null 2>&1 || fail_run "done"
LA=$("$TUXEDO" listall 2>&1) || fail_run "listall"
printf '%s\n' "$LA" | grep -E "x .*Buy milk" >/dev/null || fail_run "done-marker"
PASS=$((PASS + 1))

# 7) archive 归档完成项到 DONE_FILE，list 不再显示 Buy milk
"$TUXEDO" archive >/dev/null 2>&1 || fail_run "archive"
L2=$("$TUXEDO" list 2>&1) || fail_run "list2"
printf '%s\n' "$L2" | grep -F "Call Bob" >/dev/null || fail_run "list2-bob"
if printf '%s\n' "$L2" | grep -F "Buy milk" >/dev/null; then
    fail_run "milk-not-archived"
fi
if ! grep -F "Buy milk" "$DONE_FILE" >/dev/null 2>&1; then
    fail_run "done-file"
fi
PASS=$((PASS + 1))

printf '%s\n' "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"discovered\":${TOTAL},\"passedCount\":${PASS}}"
exit 0
