#!/usr/bin/env bash
# nmail 无头冒烟测试：纯 IO 退出路径（-v/-h/未知参数），绝不启动 TUI
set -u

NMAIL_BIN="${1:?nmail binary path}"
LD_LIBRARY_PATH_ARG="${2:-}"

export LD_LIBRARY_PATH="${LD_LIBRARY_PATH_ARG}"
export TERM=dumb
export HOME="$(mktemp -d)"

PASS=0
FAIL=0
TOTAL=0

record() {
  # record <name> <expected_exit> <actual_exit> <output_file> <grep_pattern>
  local name="$1" expected="$2" actual="$3" out="$4" pat="${5:-}"
  TOTAL=$((TOTAL + 1))
  if [ "$actual" -ne "$expected" ]; then
    echo "FAIL $name: exit=$actual expected=$expected"
    FAIL=$((FAIL + 1))
    return
  fi
  if [ -n "$pat" ] && ! grep -q "$pat" "$out"; then
    echo "FAIL $name: output missing '$pat'"
    FAIL=$((FAIL + 1))
    return
  fi
  echo "PASS $name (exit=$actual)"
  PASS=$((PASS + 1))
}

OUT=$(mktemp)

# 1) --version / -v：版本 banner + 退出 0
"$NMAIL_BIN" --version >"$OUT" 2>&1
record "--version" 0 "$?" "$OUT" "nmail"
"$NMAIL_BIN" -v >"$OUT" 2>&1
record "-v" 0 "$?" "$OUT" "nmail"

# 2) --help / -h：使用说明 + 退出 0
"$NMAIL_BIN" --help >"$OUT" 2>&1
record "--help" 0 "$?" "$OUT" "Usage: nmail"
"$NMAIL_BIN" -h >"$OUT" 2>&1
record "-h" 0 "$?" "$OUT" "Usage: nmail"

# 3) 未知参数：退出 1
"$NMAIL_BIN" --definitely-not-an-option >"$OUT" 2>&1
record "unknown-option" 1 "$?" "$OUT" "Usage: nmail"

rm -f "$OUT"

echo "NMAIL_TEST_SUMMARY total=$TOTAL pass=$PASS fail=$FAIL"
[ "$FAIL" -eq 0 ]